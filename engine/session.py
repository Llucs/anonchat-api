from json import loads as _loads
from random import randint
from time import time
from collections.abc import Generator
from uuid import uuid4
import re

from wrapper import ChatGPT as _BaseChatGPT, Headers, Challenges, VM, Log
from engine.text import TextAssembler

_RICH_BLOCK_RE = re.compile(r':::(\w+)\{.*?\}(.*?):::', re.DOTALL)

def _clean_rich_blocks(text):
    if not text:
        return text
    return _RICH_BLOCK_RE.sub(r'\2', text)

def _clean_markers(text):
    if not text:
        return text
    text = _clean_rich_blocks(text)
    while '\ue200' in text:
        start = text.index('\ue200')
        try:
            sep = text.index('\ue202', start)
            next_ue200 = text.find('\ue200', start + 1)
            if next_ue200 != -1 and sep > next_ue200:
                sep = None
        except ValueError:
            sep = None
        # Search for closing \ue201 but stop at next \ue200
        search_from = (sep if sep is not None else start) + 1
        next_ue200 = text.find('\ue200', search_from)
        end_pos = text.find('\ue201', search_from)
        if end_pos != -1 and next_ue200 != -1 and end_pos > next_ue200:
            end = None
        elif end_pos == -1:
            end = None
        else:
            end = end_pos
        if sep is None and end is None:
            text = text[:start] + text[start + 1:]
            continue
        if sep is None:
            text = text[:start] + text[end + 1:]
            continue
        if end is None:
            after = text[sep + 1:]
            if after.startswith('['):
                last_sep = after.rfind('","', 0, min(len(after), 200))
                if last_sep != -1:
                    content_start = last_sep + 3
                    text = text[:start] + after[content_start:]
                elif after.startswith('[["') or after.startswith('["'):
                    text = text[:start]
                else:
                    text = text[:start] + after
            else:
                text = text[:start] + after
            continue
        inner = text[sep+1:end]
        replacement = ''
        if inner.startswith('['):
            try:
                items = _loads(inner)
                if isinstance(items, list) and len(items) > 1:
                    replacement = items[1] if isinstance(items[1], str) else ''
                elif isinstance(items, list) and items:
                    replacement = items[-1] if isinstance(items[-1], str) else ''
            except Exception:
                pass
        text = text[:start] + replacement + text[end+1:]
    return text


class ChatGPT(_BaseChatGPT):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_slug = None
        self.conversation_id = None
        self.message_id = None
        self.parent_message_id = None
        self.resume_token = None
        self.rate_limits = None
        self.blocked_features = None
        self.model_limits = None
        self.citations = None
        self.content_references = None
        self.finish_details = None
        self.did_reasoning = False
        self.plan_type = None
        self.cluster_region = None
        self.harness = None
        self.turn_use_case = None
        self.server_ttfvt_ms = None
        self._turn_index = 2000
        self._requested_model = 'auto'

    def _reset_meta(self):
        self.model_slug = None
        self.message_id = None
        self.citations = None
        self.content_references = None
        self.finish_details = None
        self.did_reasoning = False
        self.server_ttfvt_ms = None

    def _parse_event_stream(self, stream_data: str) -> str:
        self._reset_meta()
        assem = TextAssembler()
        seen_assistant = False

        for line in stream_data.strip().split('\n'):
            if not line.startswith('data:'):
                continue

            data_str = line[5:].strip()
            if data_str == '[DONE]':
                break

            try:
                data = _loads(data_str)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue

            t = data.get('type')

            if t == 'server_ste_metadata':
                m = data.get('metadata', {})
                self.model_slug = m.get('model_slug')
                self.did_reasoning = m.get('did_auto_switch_to_reasoning', False)
                self.plan_type = m.get('plan_type')
                self.cluster_region = m.get('cluster_region')
                self.harness = m.get('harness')
                self.turn_use_case = m.get('turn_use_case')
                self.server_ttfvt_ms = m.get('server_ttfvt_ms')

            if t == 'conversation_detail_metadata':
                self.rate_limits = data.get('limits_progress')
                self.blocked_features = data.get('blocked_features')
                self.model_limits = data.get('model_limits')

            if t == 'resume_conversation_token':
                self.resume_token = data.get('token')

            if data.get('o') == 'patch' and isinstance(data.get('v'), list):
                for op in data.get('v'):
                    if op.get('p') == '/message/metadata':
                        meta = op.get('v', {})
                        slug = meta.get('resolved_model_slug')
                        if slug:
                            self.model_slug = slug
                        if meta.get('citations'):
                            self.citations = meta['citations']
                        if meta.get('content_references'):
                            self.content_references = meta['content_references']
                        if meta.get('finish_details'):
                            self.finish_details = meta['finish_details']

            v = data.get('v', {})
            if isinstance(v, dict):
                msg = v.get('message', {})
                if isinstance(msg, dict):
                    role = msg.get('author', {}).get('role')
                    if role == 'assistant':
                        seen_assistant = True
                        initial = msg.get('content', {}).get('parts', [])
                        if initial:
                            first = initial[0]
                            if isinstance(first, str):
                                assem.absorb(first, full_snapshot=True)
                        meta = msg.get('metadata', {})
                        if meta.get('citations'):
                            self.citations = meta['citations']
                        if meta.get('content_references'):
                            self.content_references = meta['content_references']
                        if meta.get('finish_details'):
                            self.finish_details = meta['finish_details']
                        mid = msg.get('id')
                        if mid:
                            self.message_id = mid

                        tc = msg.get('tool_calls') or meta.get('tool_calls')
                        if tc:
                            self._tool_calls = tc
                    elif role == 'user':
                        mid = msg.get('id')
                        if mid and not self.message_id:
                            self.parent_message_id = mid

            if data.get('o') == 'append' and data.get('p') == '/message/content/parts/0':
                part = data.get('v')
                if isinstance(part, str):
                    assem.absorb(part)
            elif data.get('o') == 'patch' and isinstance(data.get('v'), list) and seen_assistant:
                for op in data.get('v'):
                    if op.get('o') == 'append' and op.get('p') == '/message/content/parts/0':
                        part = op.get('v')
                        if isinstance(part, str):
                            assem.absorb(part)
            elif 'v' in data and isinstance(data['v'], str) and seen_assistant:
                v = data['v']
                if re.fullmatch(r'[\w-]{30,}', v):
                    continue
                assem.absorb(v)

        return _clean_markers(assem.text())

    def _extract_reasoning(self, text: str):
        # The anonymous guest backend never separates a reasoning block from
        # the final answer in the SSE it emits (probed live: a single
        # assistant stream, did_auto_switch_to_reasoning=false). The old
        # heuristic split on the first double space, which lands inside the
        # indentation of markdown code blocks and tears replies in half.
        # Without a real delimiter there is nothing to extract, so the full
        # text is content.
        return text, ''

    def converse(self, message: str, image: str = None,
                 conversation_id: str = None, parent_message_id: str = None,
                 model: str = None, tools: list = None,
                 tool_results: list = None, tool_choice: str = None,
                 temperature: float = None, top_p: float = None,
                 stop: str | list[str] = None, max_tokens: int = None,
                 max_completion_tokens: int = None, seed: int = None,
                 frequency_penalty: float = None,
                 presence_penalty: float = None) -> dict:
        self._reset_meta()
        self.resume_token = None
        self.rate_limits = None
        self._requested_model = model or 'auto'
        self._tool_calls = None
        self.chat_params = {
            'temperature': temperature,
            'top_p': top_p,
            'stop': stop,
            'max_tokens': max_completion_tokens or max_tokens,
            'seed': seed,
            'frequency_penalty': frequency_penalty,
            'presence_penalty': presence_penalty,
        }
        self._apply_chat_params()

        original_post = self.session.post
        def _patched_post(url, **kwargs):
            if 'json' in kwargs and 'model' in kwargs['json']:
                kwargs['json']['model'] = self._requested_model
                for _k, _v in self.chat_params.items():
                    if _v is not None and _k not in kwargs['json']:
                        kwargs['json'][_k] = _v
            if tools and 'json' in kwargs:
                kwargs['json']['tools'] = tools
            if tool_choice and 'json' in kwargs:
                kwargs['json']['tool_choice'] = tool_choice
            if 'timeout' not in kwargs:
                kwargs['timeout'] = 30
            return original_post(url, **kwargs)
        self.session.post = _patched_post

        try:
            if tool_results and conversation_id and parent_message_id:
                self._send_tool_results(tool_results, conversation_id, parent_message_id)
            elif image:
                self.start_with_image(message, image)
            elif conversation_id and parent_message_id:
                self._send_followup(message, conversation_id, parent_message_id)
            else:
                self.ask_question(message)
        finally:
            self.session.post = original_post

        conv_id = self.data.get('conversation_id') or self.conversation_id
        parent_id = self.data.get('parent_message_id') or self.parent_message_id
        self.data['conversation_id'] = conv_id
        self.data['parent_message_id'] = parent_id

        text = self.response

        tool_calls = getattr(self, '_tool_calls', None)
        if tool_calls and not (text and text.strip()):
            finish_reason = 'tool_calls'
            reasoning_text = ''
        else:
            finish_reason = 'stop'
            text, reasoning_text = self._extract_reasoning(text)

        return {
            'text': text,
            'reasoning': reasoning_text,
            'model': self.model_slug,
            'conversation_id': conv_id,
            'message_id': self.message_id,
            'parent_message_id': parent_id,
            'resume_token': self.resume_token,
            'rate_limits': self.rate_limits,
            'blocked_features': self.blocked_features,
            'model_limits': self.model_limits,
            'citations': self.citations,
            'content_references': self.content_references,
            'finish_details': self.finish_details,
            'did_reasoning': self.did_reasoning,
            'plan_type': self.plan_type,
            'cluster_region': self.cluster_region,
            'harness': self.harness,
            'turn_use_case': self.turn_use_case,
            'server_ttfvt_ms': self.server_ttfvt_ms,
            'tool_calls': tool_calls,
            'finish_reason': finish_reason,
        }

    def converse_stream(self, message: str, image: str = None,
                        conversation_id: str = None, parent_message_id: str = None,
                        model: str = None, tools: list = None,
                        tool_choice: str = None, temperature: float = None,
                        top_p: float = None, stop: str | list[str] = None,
                        max_tokens: int = None, max_completion_tokens: int = None,
                        seed: int = None, frequency_penalty: float = None,
                        presence_penalty: float = None) -> Generator[dict, None, None]:
        self._reset_meta()
        self.resume_token = None
        self.rate_limits = None
        self._requested_model = model or 'auto'
        self._tool_calls = None
        self.chat_params = {
            'temperature': temperature,
            'top_p': top_p,
            'stop': stop,
            'max_tokens': max_completion_tokens or max_tokens,
            'seed': seed,
            'frequency_penalty': frequency_penalty,
            'presence_penalty': presence_penalty,
        }
        self._apply_chat_params()

        yield {'type': 'meta', 'model': self._requested_model}

        pending_rich_prefix = False

        try:
            for chunk in self.start_conversation_stream(
                message,
                tools=tools,
                tool_choice=tool_choice,
            ):
                cleaned = _clean_markers(chunk)
                if not cleaned:
                    continue
                if pending_rich_prefix:
                    close_idx = cleaned.find('}')
                    if close_idx != -1:
                        cleaned = cleaned[close_idx + 1:]
                        pending_rich_prefix = False
                    else:
                        continue
                if ':::' in cleaned:
                    cleaned = re.sub(r':::\w+(?:\{[^}]*\})?', '', cleaned)
                    cleaned = cleaned.replace(':::', '')
                if cleaned.startswith('{') and re.match(r'\{[^}]*=\s*["\']', cleaned):
                    close_idx = cleaned.find('}')
                    if close_idx != -1:
                        cleaned = cleaned[close_idx + 1:]
                    else:
                        pending_rich_prefix = True
                        continue
                if cleaned:
                    yield {'type': 'chunk', 'text': cleaned}
        except SystemExit:
            yield {'type': 'error', 'error': 'IP flagged by ChatGPT'}
            return
        except RuntimeError as e:
            yield {'type': 'error', 'error': str(e)}
            return

        yield {
            'type': 'done',
            'model': self.model_slug,
            'conversation_id': self.data.get('conversation_id') or self.conversation_id,
            'message_id': self.message_id,
            'parent_message_id': self.data.get('parent_message_id') or self.parent_message_id,
        }

    def _apply_chat_params(self):
        for k, v in list(self.chat_params.items()):
            if v is None:
                self.chat_params.pop(k)
            elif k == 'stop' and isinstance(v, str):
                self.chat_params['stop'] = [v]
        self.chat_params.setdefault('max_tokens', None)

    def _run_conversation(self, messages: list) -> None:
        """Run one guest-backend turn (follow-up or tool results).

        Both turn types share the same machinery: tokens, proof-of-work,
        turnstile, headers, and the identical envelope payload. Only the
        ``messages`` list differs.
        """
        if not self.data.get('prod'):
            self._fetch_cookies()

        conduit_token = self.get_conduit(next=True)

        self._get_tokens(randint(self._turn_index, self._turn_index + 1000))
        self._turn_index += 3000

        time_1 = randint(self._turn_index, self._turn_index + 3000)
        proof_token = Challenges.solve_pow(
            self.data['proofofwork']['seed'],
            self.data['proofofwork']['difficulty'],
            self.data['config']
        )
        if not proof_token:
            raise RuntimeError("Failed to solve POW for conversation turn")
        turnstile_token = VM.get_turnstile(
            self.data['bytecode'],
            self.data['vm_token'],
            str(self.ip_info[:-1])
        )

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'

        self.session.headers = dict(Headers.CONVERSATION)
        self.session.headers.update({
            'oai-client-version': self.data['prod'],
            'oai-device-id': self.data['device-id'],
            'oai-echo-logs': f'0,{time_1},1,{time_1 + randint(1000, 1200)}',
            'openai-sentinel-chat-requirements-token': self.data['token'],
            'openai-sentinel-proof-token': proof_token,
            'openai-sentinel-turnstile-token': turnstile_token,
            'x-conduit-token': conduit_token,
        })

        payload = {
            'action': 'next',
            'messages': messages,
            'conversation_id': self.data.get('conversation_id', ''),
            'parent_message_id': self.data.get('parent_message_id', ''),
            'model': 'auto',
            'timezone_offset_min': self.timezone_offset,
            'timezone': tz_name,
            'history_and_training_disabled': True,
            'conversation_mode': {'kind': 'primary_assistant'},
            'enable_message_followups': True,
            'system_hints': [],
            'supports_buffering': True,
            'supported_encodings': ['v1'],
            'client_contextual_info': dict(self.browser_metrics),
        }

        r = self.session.post('https://chatgpt.com/backend-anon/f/conversation', json=payload, timeout=30)
        self.session.cookies.update(r.cookies)
        if 'Unusual activity' in r.text:
            Log.Error('IP flagged by ChatGPT')
            raise SystemExit(r.status_code)

        self.response = self._parse_event_stream(r.text)

    def _send_tool_results(self, tool_results: list, conversation_id: str, parent_message_id: str):
        if not self.data.get('prod'):
            self._fetch_cookies()

        self.data['conversation_id'] = conversation_id
        self.data['parent_message_id'] = parent_message_id
        self.conversation_id = conversation_id
        self.parent_message_id = parent_message_id

        messages = []
        for tr in tool_results:
            messages.append({
                'id': str(uuid4()),
                'author': {'role': 'tool'},
                'create_time': round(time(), 3),
                'content': {'content_type': 'text', 'parts': [str(tr.get('content', ''))]},
                'metadata': {'tool_call_id': tr.get('tool_call_id', '')},
            })

        self._run_conversation(messages)

        self.data['conversation_id'] = conversation_id
        self.conversation_id = conversation_id

    def _send_followup(self, message: str, conversation_id: str, parent_message_id: str):
        if not self.data.get('prod'):
            self._fetch_cookies()

        self.data['conversation_id'] = conversation_id
        self.data['parent_message_id'] = parent_message_id
        self.conversation_id = conversation_id
        self.parent_message_id = parent_message_id

        messages = [{
            'id': str(uuid4()),
            'author': {'role': 'user'},
            'create_time': round(time(), 3),
            'content': {'content_type': 'text', 'parts': [message]},
            'metadata': {},
        }]

        self._run_conversation(messages)

        self.data['conversation_id'] = conversation_id
        self.conversation_id = conversation_id
