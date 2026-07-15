from json import loads

from wrapper import ChatGPT as _BaseChatGPT


class ChatGPT(_BaseChatGPT):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_slug = None

    def _parse_event_stream(self, stream_data: str) -> str:
        parts = []

        for line in stream_data.strip().split('\n'):
            if not line.startswith('data:'):
                continue

            data_str = line[5:].strip()
            if data_str == '[DONE]':
                break

            data = loads(data_str)
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

            if data.get('o') == 'append' and data.get('p') == '/message/content/parts/0':
                parts.append(data.get('v'))
            elif data.get('o') == 'patch' and isinstance(data.get('v'), list):
                for op in data.get('v'):
                    if op.get('o') == 'append' and op.get('p') == '/message/content/parts/0':
                        parts.append(op.get('v'))
            elif 'v' in data and isinstance(data['v'], str):
                parts.append(data['v'])

        return ''.join(parts)

    def ask(self, message: str) -> dict:
        self.model_slug = None
        self.ask_question(message)
        return {
            'text': self.response,
            'model': self.model_slug,
        }
