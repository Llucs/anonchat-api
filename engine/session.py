from json import loads as _loads

from wrapper import ChatGPT as _BaseChatGPT


class ChatGPT(_BaseChatGPT):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_slug = None

    def _parse_event_stream(self, stream_data: str) -> str:
        parts = []
        seen_assistant = False

        for line in stream_data.strip().split('\n'):
            if not line.startswith('data:'):
                continue

            data_str = line[5:].strip()
            if data_str == '[DONE]':
                break

            data = _loads(data_str)
            if not isinstance(data, dict):
                continue

            if data.get('type') == 'server_ste_metadata':
                self.model_slug = data['metadata'].get('model_slug')

            if data.get('o') == 'patch' and isinstance(data.get('v'), list):
                for op in data.get('v'):
                    if op.get('p') == '/message/metadata':
                        slug = op.get('v', {}).get('resolved_model_slug')
                        if slug:
                            self.model_slug = slug

            if data.get('o') == 'add' and data.get('p') == '':
                v = data.get('v', {})
                msg = v.get('message', {})
                if msg.get('author', {}).get('role') == 'assistant':
                    seen_assistant = True
                    initial = msg.get('content', {}).get('parts', [])
                    if initial and initial[0]:
                        parts.append(initial[0])

            if data.get('o') == 'append' and data.get('p') == '/message/content/parts/0':
                parts.append(data.get('v'))
            elif data.get('o') == 'patch' and isinstance(data.get('v'), list) and seen_assistant:
                for op in data.get('v'):
                    if op.get('o') == 'append' and op.get('p') == '/message/content/parts/0':
                        parts.append(op.get('v'))
            elif 'v' in data and isinstance(data['v'], str) and seen_assistant:
                parts.append(data['v'])

        text = ''.join(parts)
        while '\ue200' in text:
            start = text.index('\ue200')
            sep = text.index('\ue202', start)
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
                        name = items[1] if isinstance(items[1], str) else ''
                        replacement = name if name else (items[-1] if isinstance(items[-1], str) else '')
                    elif isinstance(items, list) and items:
                        replacement = items[-1] if isinstance(items[-1], str) else ''
                except Exception:
                    pass
            text = text[:start] + replacement + text[end+1:]
        return text

    def ask(self, message: str) -> dict:
        self.model_slug = None
        self.ask_question(message)
        return {
            'text': self.response,
            'model': self.model_slug,
        }
