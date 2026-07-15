import json as _json
import logging
from time import time
from uuid import uuid4
from typing import Optional

from engine.session import ChatGPT
from engine.response import build_chat_response, build_stream_chunk

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
    from fastapi import FastAPI
    from fastapi.responses import StreamingResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
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

    class ResponseFormat(BaseModel):
        type: str = 'text'

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
        response_format: ResponseFormat | None = None
        extended: bool = False

    app = FastAPI(title='anonchat-api', version='1.0.0')

    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.post('/v1/chat/completions')
    async def chat_completions(req: ChatRequest):
        if not req.messages:
            return JSONResponse(content={'error': {'message': 'messages is required', 'type': 'invalid_request_error', 'code': 'invalid_request_error', 'param': None}}, status_code=400)

        last_msg = next((m for m in reversed(req.messages) if m.role == 'user'), None)
        if not last_msg:
            return JSONResponse(content={'error': {'message': 'No user message found', 'type': 'invalid_request_error', 'code': 'invalid_request_error', 'param': None}}, status_code=400)

        system_msg = next((m for m in req.messages if m.role == 'system'), None)
        system_prompt = system_msg.content if system_msg else None

        prompt_parts = []
        for m in req.messages:
            role = m.role
            content = m.content or ''
            if role == 'system':
                prompt_parts.append(f'system: {content}')
            elif role == 'user':
                prompt_parts.append(f'user: {content}')
            elif role == 'assistant':
                prompt_parts.append(f'assistant: {content}')
            elif role == 'tool':
                prompt_parts.append(f'tool ({m.tool_call_id}): {content}')
        prompt_text = '\n'.join(prompt_parts)

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

            if system_prompt and not req.conversation_id:
                message_text = f"[System: {system_prompt}]\n\n{last_msg.content or ''}"
            else:
                message_text = last_msg.content or ''

            image_param = None
            if image:
                if image.startswith('data:image') or not image.startswith('http'):
                    image_param = image
                else:
                    image_param = image
        except SystemExit:
            return JSONResponse(content={'error': {'message': 'IP flagged by ChatGPT. Use a different IP or proxy.', 'type': 'ip_flagged', 'code': 'ip_flagged', 'param': None}}, status_code=502)

        if req.stream:
            now = int(time())
            msg_id = f'chatcmpl-{uuid4().hex[:16]}'

            def stream():
                yield f'data: {_json.dumps(build_stream_chunk(msg_id, now, req.model, {"role": "assistant", "content": ""}))}\n\n'
                try:
                    for event in client.converse_stream(
                        message=message_text,
                        image=image_param,
                        conversation_id=conv_id,
                        parent_message_id=parent_id,
                        model=requested_model,
                    ):
                        if event['type'] == 'chunk':
                            chunk_data = build_stream_chunk(msg_id, now, req.model, {'content': event['text']})
                            yield f'data: {_json.dumps(chunk_data)}\n\n'
                        elif event['type'] == 'done':
                            model = event.get('model') or req.model
                            if model and model != 'auto':
                                _known_models.add(model)
                        elif event['type'] == 'error':
                            chunk_data = build_stream_chunk(msg_id, now, req.model, {}, 'error')
                            yield f'data: {_json.dumps(chunk_data)}\n\n'
                except Exception as e:
                    logger.exception('stream failed')
                chunk_data = build_stream_chunk(msg_id, now, req.model, {}, 'stop')
                yield f'data: {_json.dumps(chunk_data)}\n\n'
                yield 'data: [DONE]\n\n'

            return StreamingResponse(stream(), media_type='text/event-stream')

        try:
            result = client.converse(
                message=message_text,
                image=image_param,
                conversation_id=conv_id,
                parent_message_id=parent_id,
                model=requested_model,
                tools=tools_list,
                tool_results=tool_results if tool_results else None,
                tool_choice=req.tool_choice,
            )
        except SystemExit:
            return JSONResponse(content={'error': {'message': 'IP flagged by ChatGPT. Use a different IP or proxy.', 'type': 'ip_flagged', 'code': 'ip_flagged', 'param': None}}, status_code=502)
        except RuntimeError as e:
            logger.warning(f'Runtime error: {e}')
            return JSONResponse(content={'error': {'message': str(e), 'type': 'upstream_error', 'code': 'upstream_error', 'param': None}}, status_code=502)
        except Exception as e:
            logger.exception('chat failed')
            return JSONResponse(content={'error': {'message': 'An internal error occurred', 'type': 'server_error', 'code': 'server_error', 'param': None}}, status_code=500)

        if result.get('error'):
            return JSONResponse(content={'error': {'message': result.get('message', 'Unknown error'), 'type': 'upstream_error', 'code': 'upstream_error', 'param': None}}, status_code=413)

        model = result['model'] or req.model
        if model:
            _known_models.add(model)
        if result.get('model_limits'):
            for m in result['model_limits']:
                _known_models.add(m)

        global _global_rate_limits
        if result.get('rate_limits'):
            _global_rate_limits = result['rate_limits']

        body = build_chat_response(result, prompt_text, model, extended=req.extended)

        return body

    @app.get('/health')
    async def health():
        status = 'ok'
        try:
            import curl_cffi
            client = ChatGPT()
            status = 'ok'
        except Exception as e:
            logger.warning(f'Health check: {e}')
            status = 'degraded'
        return {
            'status': status,
            'version': '1.0.0',
            'models_known': len(_known_models),
        }

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
