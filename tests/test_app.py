import unittest
from unittest import mock

from fastapi.testclient import TestClient

import app


class FakeResponse:
    """dict-shaped result for capped (non-stream) conversations."""

    def __init__(self, text='hi there', model='gpt-5-5'):
        self.value = {
            'text': text,
            'reasoning': '',
            'model': model,
            'conversation_id': 'conv-1',
            'message_id': 'msg-1',
            'parent_message_id': 'parent-1',
            'rate_limits': None,
            'finish_reason': 'stop',
        }

    def get(self, key, default=None):
        return self.value.get(key, default)


class FakeChatGPT:
    """Stands in for engine.session.ChatGPT without touching the network."""

    instances = []

    def __init__(self, proxy=None):
        FakeChatGPT.instances.append(self)
        self.proxy = proxy
        self.converse_calls = []

    def converse(self, **kwargs):
        self.converse_calls.append(kwargs)
        return dict(FakeResponse().value)

    def converse_stream(self, **kwargs):
        self.converse_calls.append(kwargs)
        yield {'type': 'chunk', 'text': 'hel'}
        yield {'type': 'chunk', 'text': 'lo'}
        yield {'type': 'done', 'model': 'model-stream'}

    def list_models(self):
        return []


class TestApiBehaviour(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app.app)
        self._fakes = FakeChatGPT.instances
        self._fakes.clear()

    def test_health(self):
        r = self.client.get('/health')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'ok')

    def test_missing_messages(self):
        r = self.client.post('/v1/chat/completions', json={})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error']['message'], 'messages is required')
        self.assertEqual(r.json()['error']['param'], 'messages')

    def test_invalid_content_type(self):
        r = self.client.post('/v1/chat/completions',
                             json={'messages': [{'role': 'user', 'content': 123}]})
        self.assertEqual(r.status_code, 400)
        body = r.json()['error']
        self.assertEqual(body['param'], 'content')
        self.assertIn('content', body['message'])

    def test_unknown_parameter(self):
        r = self.client.post('/v1/chat/completions',
                             json={'messages': [{'role': 'user', 'content': 'x'}],
                                   'no_such_param': 1})
        self.assertEqual(r.status_code, 400)
        body = r.json()['error']
        self.assertEqual(body['type'], 'invalid_request_error')
        self.assertIn('Unknown parameter', body['message'])

    def test_invalid_json(self):
        r = self.client.post('/v1/chat/completions',
                             content=b'{not json', headers={'Content-Type': 'application/json'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('Invalid JSON payload', r.json()['error']['message'])

    def test_no_user_message(self):
        r = self.client.post('/v1/chat/completions',
                             json={'messages': [{'role': 'system', 'content': 'be nice'}]})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error']['message'], 'No user message found')

    def test_n_unsupported(self):
        r = self.client.post('/v1/chat/completions',
                             json={'messages': [{'role': 'user', 'content': 'x'}], 'n': 2})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error']['param'], 'n')

    def test_chat_completion_success(self):
        with mock.patch('app.ChatGPT', FakeChatGPT):
            r = self.client.post('/v1/chat/completions',
                                 json={'messages': [{'role': 'user', 'content': 'hi'}]})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body['object'], 'chat.completion')
        self.assertEqual(body['choices'][0]['message']['content'], 'hi there')
        self.assertIn('usage', body)

    def test_chat_completion_passes_params(self):
        with mock.patch('app.ChatGPT', FakeChatGPT):
            r = self.client.post('/v1/chat/completions', json={
                'messages': [{'role': 'user', 'content': 'hi'}],
                'temperature': 0.5,
                'max_tokens': 64,
                'seed': 42,
            })
        self.assertEqual(r.status_code, 200)
        call = FakeChatGPT.instances[0]
        self.assertEqual(call.converse_calls[0]['temperature'], 0.5)
        self.assertEqual(call.converse_calls[0]['max_tokens'], 64)

    def test_stream_success(self):
        with mock.patch('app.ChatGPT', FakeChatGPT):
            with self.client.stream('POST', '/v1/chat/completions',
                                    json={'messages': [{'role': 'user', 'content': 'hi'}],
                                          'stream': True}) as resp:
                self.assertEqual(resp.status_code, 200)
                text = resp.read().decode('utf-8')
        self.assertIn('data: ', text)
        self.assertIn('chat.completion.chunk', text)
        self.assertIn('role', text)
        self.assertIn('content', text)
        self.assertTrue(text.rstrip().endswith('data: [DONE]'))

    def test_v1_models(self):
        with mock.patch('app.ChatGPT', FakeChatGPT):
            r = self.client.get('/v1/models')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'object': 'list', 'data': []})


if __name__ == '__main__':
    unittest.main()
