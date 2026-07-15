from json import loads as _loads
from typing import Generator, Optional
import re

from wrapper import ChatGPT as _BaseChatGPT

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
        except ValueError:
            break
        try:
            end = text.index('\ue201', sep + 1)
        except ValueError:
            break
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
        parts = []
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
                        if initial and initial[0]:
                            parts.append(initial[0])
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
                parts.append(data.get('v'))
            elif data.get('o') == 'patch' and isinstance(data.get('v'), list) and seen_assistant:
                for op in data.get('v'):
                    if op.get('o') == 'append' and op.get('p') == '/message/content/parts/0':
                        parts.append(op.get('v'))
            elif 'v' in data and isinstance(data['v'], str) and seen_assistant:
                parts.append(data['v'])

        return _clean_markers(''.join(parts))

    def _extract_reasoning(self, text: str):
        reasoning_text = ''
        if '  ' in text:
            end = text.find('  ')
            if end >= 3:
                reasoning_text = text[3:end]
                text = text[end + 3:]
            else:
                reasoning_text = text[:end]
                text = text[end + 2:]
        return text, reasoning_text

    def converse(self, message: str, image: str = None,
                 conversation_id: str = None, parent_message_id: str = None,
                 model: str = None, tools: list = None,
                 tool_results: list = None, tool_choice: str = None) -> dict:
        self._reset_meta()
        self.resume_token = None
        self.rate_limits = None
        self._requested_model = model or 'auto'
        self._tool_calls = None

        original_post = self.session.post
        def _patched_post(url, **kwargs):
            if 'json' in kwargs and 'model' in kwargs['json']:
                kwargs['json']['model'] = self._requested_model
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
                        model: str = None) -> Generator[dict, None, None]:
        self._reset_meta()
        self.resume_token = None
        self.rate_limits = None
        self._requested_model = model or 'auto'
        self._tool_calls = None

        yield {'type': 'meta', 'model': self._requested_model}

        try:
            for chunk in self.start_conversation_stream(message):
                cleaned = _clean_rich_blocks(chunk)
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

    def _send_tool_results(self, tool_results: list, conversation_id: str, parent_message_id: str):
        from random import randint
        from wrapper import Headers, Challenges, VM, Log
        from uuid import uuid4
        from time import time

        if not self.data.get('prod'):
            self._fetch_cookies()

        self.data['conversation_id'] = conversation_id
        self.data['parent_message_id'] = parent_message_id
        self.conversation_id = conversation_id
        self.parent_message_id = parent_message_id

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
            raise RuntimeError("Failed to solve POW for tool results")
        turnstile_token = VM.get_turnstile(
            self.data['bytecode'],
            self.data['vm_token'],
            str(self.ip_info[:-1])
        )

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'

        self.session.headers = Headers.CONVERSATION
        self.session.headers.update({
            'oai-client-version': self.data['prod'],
            'oai-device-id': self.data['device-id'],
            'oai-echo-logs': f'0,{time_1},1,{time_1 + randint(1000, 1200)}',
            'openai-sentinel-chat-requirements-token': self.data['token'],
            'openai-sentinel-proof-token': proof_token,
            'openai-sentinel-turnstile-token': turnstile_token,
            'x-conduit-token': conduit_token,
        })

        messages = []
        for tr in tool_results:
            messages.append({
                'id': str(uuid4()),
                'author': {'role': 'tool'},
                'create_time': round(time(), 3),
                'content': {'content_type': 'text', 'parts': [str(tr.get('content', ''))]},
                'metadata': {'tool_call_id': tr.get('tool_call_id', '')},
            })

        payload = {
            'action': 'next',
            'messages': messages,
            'conversation_id': conversation_id,
            'parent_message_id': parent_message_id,
            'model': 'auto',
            'timezone_offset_min': self.timezone_offset,
            'timezone': tz_name,
            'history_and_training_disabled': True,
            'conversation_mode': {'kind': 'primary_assistant'},
            'enable_message_followups': True,
            'system_hints': [],
            'supports_buffering': True,
            'supported_encodings': ['v1'],
            'client_contextual_info': {
                'is_dark_mode': True,
                'time_since_loaded': randint(3, 6),
                'page_height': 1219,
                'page_width': 3440,
                'pixel_ratio': 1,
                'screen_height': 1440,
                'screen_width': 3440,
            },
        }

        r = self.session.post('https://chatgpt.com/backend-anon/f/conversation', json=payload, timeout=30)
        self.session.cookies.update(r.cookies)
        if 'Unusual activity' in r.text:
            Log.Error('IP flagged by ChatGPT')
            raise SystemExit(r.status_code)

        self.data['conversation_id'] = conversation_id
        self.conversation_id = conversation_id
        self.response = self._parse_event_stream(r.text)

    def _send_followup(self, message: str, conversation_id: str, parent_message_id: str):
        from random import randint
        from wrapper import Headers, Challenges, VM, Log
        from uuid import uuid4
        from time import time

        if not self.data.get('prod'):
            self._fetch_cookies()

        self.data['conversation_id'] = conversation_id
        self.data['parent_message_id'] = parent_message_id
        self.conversation_id = conversation_id
        self.parent_message_id = parent_message_id

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
            raise RuntimeError("Failed to solve POW for follow-up")
        turnstile_token = VM.get_turnstile(
            self.data['bytecode'],
            self.data['vm_token'],
            str(self.ip_info[:-1])
        )

        tz_name = self.ip_info[5] if len(self.ip_info) > 5 else 'UTC'

        self.session.headers = Headers.CONVERSATION
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
            'messages': [{
                'id': str(uuid4()),
                'author': {'role': 'user'},
                'create_time': round(time(), 3),
                'content': {'content_type': 'text', 'parts': [message]},
                'metadata': {},
            }],
            'conversation_id': conversation_id,
            'parent_message_id': parent_message_id,
            'model': 'auto',
            'timezone_offset_min': self.timezone_offset,
            'timezone': tz_name,
            'history_and_training_disabled': True,
            'conversation_mode': {'kind': 'primary_assistant'},
            'enable_message_followups': True,
            'system_hints': [],
            'supports_buffering': True,
            'supported_encodings': ['v1'],
            'client_contextual_info': {
                'is_dark_mode': True,
                'time_since_loaded': randint(3, 6),
                'page_height': 1219,
                'page_width': 3440,
                'pixel_ratio': 1,
                'screen_height': 1440,
                'screen_width': 3440,
            },
        }

        r = self.session.post('https://chatgpt.com/backend-anon/f/conversation', json=payload, timeout=30)
        self.session.cookies.update(r.cookies)

        if 'Unusual activity' in r.text:
            Log.Error('IP flagged by ChatGPT')
            raise SystemExit(r.status_code)

        self.data['conversation_id'] = conversation_id
        self.conversation_id = conversation_id
        self.response = self._parse_event_stream(r.text)
