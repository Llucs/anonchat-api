import json as _json
import logging
from time import time
from uuid import uuid4

from engine.session import ChatGPT

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('anonchat')

_known_models = set()
_global_rate_limits = None

try:
    import tiktoken
    _enc = tiktoken.get_encoding('o200k_base')
    def _count(s):
        return len(_enc.encode(s)) if s else 0
except ImportError:
    def _count(s):
        return max(1, len(s) // 4)

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
    from uvicorn import run
    _has_server = True
except ImportError:
    _has_server = False

if _has_server:

    class Message(BaseModel):
        role: str
        content: str | None = None
        tool_calls: list | None = None
        tool_call_id: str | None = None

    class ToolDef(BaseModel):
        type: str = 'function'
        function: dict

    class ChatRequest(BaseModel):
        messages: list[Message]
        model: str = 'auto'
        stream: bool = False
        proxy: str | None = None
        temperature: float | None = None
        top_p: float | None = None
        n: int | None = None
        max_tokens: int | None = None
        max_completion_tokens: int | None = None
        stop: str | list[str] | None = None
        frequency_penalty: float | None = None
        presence_penalty: float | None = None
        seed: int | None = None
        user: str | None = None
        conversation_id: str | None = None
        parent_message_id: str | None = None
        image: str | None = None
        tools: list[ToolDef] | None = None
        tool_choice: str | None = None
        extended: bool = False

    app = FastAPI(title='anonchat-api', version='1.0.0')

    @app.post('/v1/chat/completions')
    async def chat_completions(req: ChatRequest):
        last_msg = next((m for m in reversed(req.messages) if m.role == 'user'), None)
        if not last_msg:
            raise HTTPException(400, 'No user message found')

        prompt_text = '\n'.join(f'{m.role}: {m.content or ""}' for m in req.messages)

        # Find tool_result messages (role='tool')
        tool_results = []
        conv_id = req.conversation_id
        parent_id = req.parent_message_id
        for m in req.messages:
            if m.role == 'tool' and m.tool_call_id:
                tool_results.append({'tool_call_id': m.tool_call_id, 'content': m.content or ''})
            if m.role == 'assistant' and m.tool_calls:
                if not conv_id:
                    conv_id = getattr(m, 'conversation_id', None)

        try:
            client = ChatGPT(proxy=req.proxy) if req.proxy else ChatGPT()
            image = req.image
            requested_model = None if req.model == 'auto' else req.model

            tools_list = [t.model_dump() for t in req.tools] if req.tools else None

            result = client.converse(
                message=last_msg.content or '',
                image=image if (image and image.startswith('data:image') or (image and not image.startswith('http'))) else None,
                conversation_id=conv_id,
                parent_message_id=parent_id,
                model=requested_model,
                tools=tools_list,
                tool_results=tool_results if tool_results else None,
                tool_choice=req.tool_choice,
            )
        except SystemExit:
            raise HTTPException(502, 'IP flagged by ChatGPT')
        except Exception as e:
            logger.exception('chat failed')
            raise HTTPException(500, str(e))

        if result.get('error'):
            raise HTTPException(413, result['message'])

        model = result['model'] or req.model
        if model:
            _known_models.add(model)
        if result.get('model_limits'):
            for m in result['model_limits']:
                _known_models.add(m)

        global _global_rate_limits
        if result.get('rate_limits'):
            _global_rate_limits = result['rate_limits']

        now = int(time())
        msg_id = f'chatcmpl-{uuid4().hex[:16]}'
        text = result.get('text', '')
        reasoning = result.get('reasoning', '')
        citations = result.get('citations')
        content_refs = result.get('content_references')
        tool_calls = result.get('tool_calls')
        finish_reason = result.get('finish_reason', 'stop')

        pt = _count(prompt_text)
        ct = _count(text)
        rt = _count(reasoning) if reasoning else 0

        choice_msg = {'role': 'assistant', 'content': text}
        if rt:
            choice_msg['reasoning_content'] = reasoning
        if citations:
            choice_msg['citations'] = citations
        if content_refs:
            choice_msg['content_references'] = content_refs
        if tool_calls:
            choice_msg['tool_calls'] = tool_calls
            if not text:
                choice_msg['content'] = None

        choices = [{
            'index': 0,
            'message': choice_msg,
            'finish_reason': finish_reason,
        }]

        usage = {'prompt_tokens': pt, 'completion_tokens': ct, 'total_tokens': pt + ct}
        if rt:
            usage['completion_tokens_details'] = {'reasoning_tokens': rt}

        body = {
            'id': msg_id,
            'object': 'chat.completion',
            'created': now,
            'model': model,
            'choices': choices,
            'usage': usage,
        }

        if req.extended:
            for _k in ['conversation_id', 'parent_message_id', 'rate_limits',
                       'plan_type', 'cluster_region', 'did_reasoning',
                       'server_ttfvt_ms', 'resume_token']:
                _v = result.get(_k)
                if _v:
                    body[_k] = _v

        if req.stream:
            async def stream():
                def chunk(delta, finish=None):
                    d = {'id': msg_id, 'object': 'chat.completion.chunk', 'created': now, 'model': model,
                         'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                    return f'data: {_json.dumps(d)}\n\n'
                yield chunk({'role': 'assistant', 'content': ''})
                if reasoning:
                    yield chunk({'reasoning_content': reasoning})
                if tool_calls:
                    yield chunk({'tool_calls': tool_calls})
                if text:
                    yield chunk({'content': text})
                yield chunk({}, finish=finish_reason)
                yield 'data: [DONE]\n\n'

            return StreamingResponse(stream(), media_type='text/event-stream')

        return body

    @app.get('/health')
    async def health():
        return {'status': 'ok'}

    @app.get('/v1/models')
    async def list_models(refresh: bool = False):
        if refresh:
            try:
                client = ChatGPT()
                result = client.converse('hi', model='auto')
                slug = result.get('model')
                if slug and slug != 'auto':
                    _known_models.add(slug)
            except Exception as e:
                logger.warning(f'model discovery failed: {e}')

        all_models = [{'id': 'auto', 'object': 'model', 'created': 1700000000, 'owned_by': 'openai'}]
        for m in sorted(_known_models):
            if m != 'auto':
                all_models.append({'id': m, 'object': 'model', 'created': 1700000000, 'owned_by': 'openai'})
        return {'object': 'list', 'data': all_models}

    @app.get('/v1/usage')
    async def usage():
        return {
            'rate_limits': _global_rate_limits or {},
        }


if __name__ == '__main__':
    if _has_server:
        import sys as _sys
        _port = 8000
        for _i, _a in enumerate(_sys.argv):
            if _a == '--port' and _i + 1 < len(_sys.argv):
                _port = int(_sys.argv[_i + 1])
        run(app, host='0.0.0.0', port=_port, log_level='info')
    else:
        print('Server deps not installed. Install: pip install fastapi uvicorn pydantic')
        print('Or use CLI: anonchat "message"')
