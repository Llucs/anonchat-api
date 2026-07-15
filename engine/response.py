from time import time
from uuid import uuid4
from typing import Optional

try:
    import tiktoken
    _enc = tiktoken.get_encoding('o200k_base')
    def _count(s):
        return len(_enc.encode(s)) if s else 0
except ImportError:
    def _count(s):
        return max(1, len(s) // 4)


def _system_fingerprint():
    return f"fp_{uuid4().hex[:16]}"


def build_chat_response(
    result: dict,
    prompt_text: str,
    model: str,
    extended: bool = False,
    system_fingerprint: Optional[str] = None,
):
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
        'model': model or 'auto',
        'choices': choices,
        'usage': usage,
        'system_fingerprint': system_fingerprint or _system_fingerprint(),
    }

    if extended:
        for _k in ['conversation_id', 'parent_message_id', 'rate_limits',
                   'plan_type', 'cluster_region', 'did_reasoning',
                   'server_ttfvt_ms', 'resume_token']:
            _v = result.get(_k)
            if _v:
                body[_k] = _v

    return body


def build_error_response(message: str, code: str = 'server_error', status_code: int = 500):
    return {
        'error': {
            'message': message,
            'type': code,
            'code': code,
            'param': None,
        }
    }, status_code


def build_stream_chunk(msg_id: str, created: int, model: str, delta: dict, finish_reason: str = None):
    d = {
        'id': msg_id,
        'object': 'chat.completion.chunk',
        'created': created,
        'model': model,
        'choices': [{
            'index': 0,
            'delta': delta,
            'finish_reason': finish_reason,
        }],
    }
    return d
