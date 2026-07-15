import json as _json
import logging
from time import time
from uuid import uuid4

from engine.session import ChatGPT

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('anonchat')

_seen_models = set()

try:
    import tiktoken
    _enc = tiktoken.get_encoding('o200k_base')
    def _count_tokens(text):
        return len(_enc.encode(text)) if text else 0
except ImportError:
    def _count_tokens(text):
        return max(1, len(text) // 4)

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

    app = FastAPI(title='anonchat-api', version='1.0.0')

    @app.post('/v1/chat/completions')
    async def chat_completions(req: ChatRequest):
        last = next((m.content for m in reversed(req.messages) if m.role == 'user'), None)
        if not last:
            raise HTTPException(400, 'No user message found')

        prompt_text = '\n'.join(f'{m.role}: {m.content}' for m in req.messages)

        try:
            client = ChatGPT(proxy=req.proxy) if req.proxy else ChatGPT()
            result = client.ask(last)
        except SystemExit:
            raise HTTPException(502, 'IP flagged by ChatGPT - try a different proxy')
        except Exception as e:
            logger.exception('chat failed')
            raise HTTPException(500, str(e))

        model = result['model'] or req.model
        if model:
            _seen_models.add(model)

        content = result['text']
        now = int(time())
        msg_id = f'chatcmpl-{uuid4().hex[:16]}'

        reasoning_text = ''
        text = content

        if '  ' in content:
            end = content.find('  ')
            reasoning_text = content[3:end]
            text = content[end + 3:]

        prompt_tokens = _count_tokens(prompt_text)
        completion_tokens = _count_tokens(text)
        reasoning_tokens = _count_tokens(reasoning_text) if reasoning_text else 0

        choice_msg = {'role': 'assistant', 'content': text}
        if reasoning_tokens:
            choice_msg['reasoning_content'] = reasoning_text

        choices = [{
            'index': 0,
            'message': choice_msg,
            'finish_reason': 'stop',
        }]

        usage = {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens,
        }
        if reasoning_tokens:
            usage['completion_tokens_details'] = {
                'reasoning_tokens': reasoning_tokens,
            }

        body = {
            'id': msg_id,
            'object': 'chat.completion',
            'created': now,
            'model': model,
            'choices': choices,
            'usage': usage,
        }

        if req.stream:
            async def stream():
                def chunk(delta, finish=None):
                    d = {'id': msg_id, 'object': 'chat.completion.chunk', 'created': now, 'model': model,
                         'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                    return f'data: {_json.dumps(d)}\n\n'
                yield chunk({'role': 'assistant', 'content': ''})
                if reasoning_text:
                    yield chunk({'reasoning_content': reasoning_text})
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


if __name__ == '__main__':
    if _has_server:
        run(app, host='0.0.0.0', port=8000, log_level='info')
    else:
        print('Server dependencies not installed. Install with: pip install fastapi uvicorn pydantic')
        print('Or use the CLI: anonchat "your message"')
