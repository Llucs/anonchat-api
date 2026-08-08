import json as _json
import logging
from time import time
from uuid import uuid4

from engine.session import ChatGPT
from engine.response import build_model_list, build_chat_response, build_stream_chunk, _count

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('anonchat')

_global_rate_limits = None

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.exceptions import RequestValidationError
    from pydantic import BaseModel
    from uvicorn import run
    _has_server = True
except ImportError:
    _has_server = False

if _has_server:

    class Message(BaseModel):
        role: str
        content: str | list | None = None
        tool_calls: list | None = None
        tool_call_id: str | None = None

    class ToolDef(BaseModel):
        type: str = 'function'
        function: dict

    class ResponseFormat(BaseModel):
        type: str = 'text'

    class StreamOptions(BaseModel):
        include_usage: bool = False

    class ChatRequest(BaseModel):
        model_config = {'extra': 'forbid'}

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
        stream_options: StreamOptions | None = None

    app = FastAPI(title='anonchat-api', version='1.0.0')

    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=False,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    def _error(message: str, status_code: int = 400, code: str = 'invalid_request_error', param=None):
        return JSONResponse(
            content={'error': {'message': message, 'type': code, 'code': code, 'param': param}},
            status_code=status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        errors = getattr(exc, 'errors', lambda: [])()
        if not errors:
            message = 'Invalid request'
            param = None
        else:
            first = errors[0]
            loc = first.get('loc', [])
            msg = str(first.get('msg', ''))
            if msg == 'JSON decode error':
                message = 'Invalid JSON payload: could not parse the request body.'
                param = None
            elif msg.startswith('Field required') and 'messages' in loc:
                message = 'messages is required'
                param = 'messages'
            else:
                if 'content' in loc:
                    param = 'content'
                    message = 'Invalid value for content'
                else:
                    param = next((str(x) for x in reversed(loc) if isinstance(x, str)), None)
                    if msg.startswith('Extra inputs are not permitted'):
                        message = f"Unknown parameter: '{param}'."
                    elif param == 'model':
                        message = 'Invalid value for model'
                    else:
                        message = f'Invalid value for {param}: {msg}'
        return _error(message, 400, 'invalid_request_error', param)

    def _flatten_content(content, images: list) -> str:
        """Flatten OpenAI-style content (str or list of parts) to plain text."""
        if content is None:
            return ''
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for p in content:
                if isinstance(p, str):
                    parts.append(p)
                elif isinstance(p, dict):
                    t = p.get('type')
                    if t == 'text':
                        parts.append(str(p.get('text', '')))
                    elif t in ('image_url', 'input_image'):
                        img = p.get('image_url') or {}
                        url = img if isinstance(img, str) else img.get('url', '')
                        if url:
                            images.append(url)
            return '\n'.join(x for x in parts if x)
        return str(content)

    def _build_prompt(messages: list, images: list) -> tuple[str, str, str, str | None]:
        """Flatten the conversation into a single guest-mode prompt.

        Returns (prompt_text, image_param, last_user_message, system_prompt).
        """
        system_prompt = None
        turns = []
        last_user = None
        for m in messages:
            content = _flatten_content(m.content, images)
            if m.role == 'system':
                system_prompt = content or None
            elif m.role == 'user':
                if content:
                    last_user = content
                    turns.append(f'user: {content}')
                else:
                    turns.append('user: (empty)')
            elif m.role == 'assistant':
                if m.content:
                    turns.append(f'assistant: {content}')
                elif m.tool_calls:
                    calls = _json.dumps(m.tool_calls)[:500]
                    turns.append(f'assistant: [tool calls: {calls}]')
                else:
                    turns.append('assistant: (empty)')
            elif m.role == 'tool':
                turns.append(f'tool ({m.tool_call_id}): {content}')
        prompt_text = '\n'.join(turns)
        image_param = None
        if images:
            image_param = images[0]
        return prompt_text, image_param, last_user, system_prompt

    def _stream_error(message: str, code: str = 'upstream_error') -> str:
        return f'data: {_json.dumps({"error": {"message": message, "type": code, "code": code, "param": None}})}\n\n'

    @app.post('/v1/chat/completions')
    async def chat_completions(req: ChatRequest):
        if not req.messages:
            return _error('messages is required', 400)

        if req.n is not None and req.n != 1:
            return _error('n is not supported by this API (only n=1)', 400, 'unsupported_parameter', 'n')

        if req.response_format is not None and req.response_format.type not in ('text', 'none'):
            return _error(
                'response_format is not supported by this API',
                400,
                'unsupported_parameter',
                'response_format',
            )

        images: list = []
        prompt_text, image_param, last_user, system_prompt = _build_prompt(req.messages, images)
        if not images and req.image:
            images.append(req.image)
            image_param = req.image

        if last_user is None:
            return _error('No user message found', 400)

        # Resuming an existing conversation? The guest backend keeps that
        # history server-side, so only the new user turn is sent. Otherwise
        # the flattened transcript is sent to preserve multi-turn memory.
        resume = bool(req.conversation_id and req.parent_message_id)
        if resume:
            message_text = last_user
        elif system_prompt:
            message_text = f"[System: {system_prompt}]\n\n{prompt_text}"
        else:
            message_text = prompt_text

        # Use the transcript actually transmitted for token accounting.
        prompt_for_tokens = message_text

        conv_id = req.conversation_id
        parent_id = req.parent_message_id
        tools_list = [t.model_dump() for t in req.tools] if req.tools else None

        if req.stream:
            now = int(time())
            msg_id = f'chatcmpl-{uuid4().hex[:16]}'
            model = req.model

            def stream():
                client = None
                try:
                    client = ChatGPT(proxy=req.proxy) if req.proxy else ChatGPT()
                except SystemExit:
                    yield _stream_error('IP flagged by ChatGPT. Use a different IP or proxy.', 'ip_flagged')
                    return
                except Exception:
                    logger.exception('failed to create client')
                    yield _stream_error('Failed to initialize guest session')
                    return

                role_delta = build_stream_chunk(msg_id, now, model, {"role": "assistant", "content": ""})
                yield f'data: {_json.dumps(role_delta)}\n\n'
                streamed_text = []
                final_model = model
                try:
                    for event in client.converse_stream(
                            message=message_text,
                            image=image_param,
                            conversation_id=conv_id,
                            parent_message_id=parent_id,
                            model=None if req.model == 'auto' else req.model,
                            tools=tools_list,
                            tool_choice=req.tool_choice,
                            temperature=req.temperature,
                            top_p=req.top_p,
                            stop=req.stop,
                            max_tokens=req.max_tokens,
                            max_completion_tokens=req.max_completion_tokens,
                            seed=req.seed,
                            frequency_penalty=req.frequency_penalty,
                            presence_penalty=req.presence_penalty,
                    ):
                        if event['type'] == 'chunk':
                            streamed_text.append(event['text'])
                            chunk_data = build_stream_chunk(msg_id, now, model, {'content': event['text']})
                            yield f'data: {_json.dumps(chunk_data)}\n\n'
                        elif event['type'] == 'done':
                            final_model = event.get('model') or model
                        elif event['type'] == 'error':
                            logger.error(f'upstream streaming error: {event.get("error")}')
                except SystemExit:
                    logger.error('IP flagged during stream')
                    yield _stream_error('IP flagged by ChatGPT. Use a different IP or proxy.', 'ip_flagged')
                    return
                except Exception:
                    logger.exception('stream failed')
                    yield _stream_error('An internal error occurred', 'server_error')
                    return

                usage = None
                if req.stream_options is not None and req.stream_options.include_usage:
                    usage = {
                        'prompt_tokens': _count(prompt_for_tokens),
                        'completion_tokens': _count(''.join(streamed_text)),
                        'total_tokens': _count(prompt_for_tokens) + _count(''.join(streamed_text)),
                    }

                stop_chunk = build_stream_chunk(msg_id, now, final_model, {}, 'stop', usage=usage)
                yield f'data: {_json.dumps(stop_chunk)}\n\n'
                yield 'data: [DONE]\n\n'

            return StreamingResponse(stream(), media_type='text/event-stream')

        try:
            client = ChatGPT(proxy=req.proxy) if req.proxy else ChatGPT()
        except SystemExit:
            return _error('IP flagged by ChatGPT. Use a different IP or proxy.', 502, 'ip_flagged')
        except RuntimeError as e:
            return _error(str(e), 502, 'upstream_error')
        except Exception:
            logger.exception('client init failed')
            return _error('Failed to initialize guest session', 502, 'upstream_error')

        tool_results = []
        for m in req.messages:
            if m.role == 'tool' and m.tool_call_id:
                tool_results.append({'tool_call_id': m.tool_call_id, 'content': m.content or ''})

        try:
            result = client.converse(
                message=message_text,
                image=image_param,
                conversation_id=conv_id,
                parent_message_id=parent_id,
                model=None if req.model == 'auto' else req.model,
                tools=tools_list,
                tool_results=tool_results if tool_results else None,
                tool_choice=req.tool_choice,
                temperature=req.temperature,
                top_p=req.top_p,
                stop=req.stop,
                max_tokens=req.max_tokens,
                max_completion_tokens=req.max_completion_tokens,
                seed=req.seed,
                frequency_penalty=req.frequency_penalty,
                presence_penalty=req.presence_penalty,
            )
        except SystemExit:
            return _error('IP flagged by ChatGPT. Use a different IP or proxy.', 502, 'ip_flagged')
        except RuntimeError as e:
            logger.warning(f'Runtime error: {e}')
            return _error(str(e), 502, 'upstream_error')
        except Exception:
            logger.exception('chat failed')
            return _error('An internal error occurred', 500, 'server_error')

        global _global_rate_limits
        if result.get('rate_limits'):
            _global_rate_limits = result['rate_limits']

        model_out = result.get('model') or req.model
        body = build_chat_response(result, prompt_for_tokens, model_out, extended=req.extended)
        return body

    @app.get('/health')
    async def health():
        return {
            'status': 'ok',
            'version': '1.0.0',
        }

    @app.get('/v1/models')
    async def list_models():
        try:
            client = ChatGPT()
            models = client.list_models()
        except Exception as e:
            logger.warning(f'model discovery failed: {e}')
            models = []

        return build_model_list(models)

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
                try:
                    _port = int(_sys.argv[_i + 1])
                except ValueError:
                    print(f'error: invalid port "{_sys.argv[_i + 1]}"', file=_sys.stderr)
                    _sys.exit(1)
        run(app, host='0.0.0.0', port=_port, log_level='info')
    else:
        print('Server deps not installed. Install: pip install fastapi uvicorn pydantic')
        print('Or use CLI: anonchat "message"')
