import json as _json
import logging
from time import time
from uuid import uuid4

from engine.session import ChatGPT

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('anonchat')

_seen_models = set()
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
        content: str

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

    app = FastAPI(title='anonchat-api', version='1.0.0')

    @app.post('/v1/chat/completions')
    async def chat_completions(req: ChatRequest):
        last = next((m.content for m in reversed(req.messages) if m.role == 'user'), None)
        if not last:
            raise HTTPException(400, 'No user message found')

        prompt_text = '\n'.join(f'{m.role}: {m.content}' for m in req.messages)

        try:
            client = ChatGPT(proxy=req.proxy) if req.proxy else ChatGPT()
            image = req.image
            result = client.converse(
                message=last,
                image=image if (image and image.startswith('data:image') or (image and not image.startswith('http'))) else None,
                conversation_id=req.conversation_id,
                parent_message_id=req.parent_message_id,
            )
        except SystemExit:
            raise HTTPException(502, 'IP flagged by ChatGPT')
        except Exception as e:
            logger.exception('chat failed')
            raise HTTPException(500, str(e))

        model = result['model'] or req.model
        if model:
            _seen_models.add(model)

        global _global_rate_limits
        if result.get('rate_limits'):
            _global_rate_limits = result['rate_limits']

        now = int(time())
        msg_id = f'chatcmpl-{uuid4().hex[:16]}'
        text = result['text']
        reasoning = result.get('reasoning', '')
        citations = result.get('citations')
        content_refs = result.get('content_references')

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

        choices = [{
            'index': 0,
            'message': choice_msg,
            'finish_reason': 'stop',
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

        conv_id = result.get('conversation_id')
        parent_id = result.get('parent_message_id')
        if conv_id:
            body['conversation_id'] = conv_id
        if parent_id:
            body['parent_message_id'] = parent_id
        if result.get('rate_limits'):
            body['rate_limits'] = result['rate_limits']
        if result.get('plan_type'):
            body['plan_type'] = result['plan_type']
        if result.get('cluster_region'):
            body['cluster_region'] = result['cluster_region']
        if result.get('did_reasoning'):
            body['did_reasoning'] = True
        if result.get('server_ttfvt_ms'):
            body['server_ttfvt_ms'] = result['server_ttfvt_ms']
        if result.get('resume_token'):
            body['resume_token'] = result['resume_token']

        if req.stream:
            async def stream():
                def chunk(delta, finish=None):
                    d = {'id': msg_id, 'object': 'chat.completion.chunk', 'created': now, 'model': model,
                         'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                    return f'data: {_json.dumps(d)}\n\n'
                yield chunk({'role': 'assistant', 'content': ''})
                if reasoning:
                    yield chunk({'reasoning_content': reasoning})
                yield chunk({'content': text})
                yield chunk({}, finish='stop')
                yield 'data: [DONE]\n\n'

            return StreamingResponse(stream(), media_type='text/event-stream')

        return body

    @app.get('/health')
    async def health():
        return {'status': 'ok'}

    @app.get('/v1/models')
    async def list_models():
        models = [{'id': 'auto', 'object': 'model', 'created': 1700000000, 'owned_by': 'openai'}]
        for m in sorted(_seen_models):
            if m != 'auto':
                models.append({'id': m, 'object': 'model', 'created': 1700000000, 'owned_by': 'openai'})
        return {'object': 'list', 'data': models}

    @app.get('/v1/usage')
    async def usage():
        return {
            'rate_limits': _global_rate_limits or {},
        }


if __name__ == '__main__':
    if _has_server:
        run(app, host='0.0.0.0', port=8000, log_level='info')
    else:
        print('Server deps not installed. Install: pip install fastapi uvicorn pydantic')
        print('Or use CLI: anonchat "message"')
