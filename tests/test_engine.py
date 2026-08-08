import unittest
from unittest import mock

import engine.session


class TestBuildPayload(unittest.TestCase):

    @staticmethod
    def _client():
        with mock.patch('wrapper.chatgpt.IP_Info.fetch_info',
                        return_value=['1.2.3.4', 'X', 'Y', '0', '0', 'UTC']):
            return engine.session.ChatGPT(cookies={'oai-did': 'test'})

    def test_default_new_conversation(self):
        c = self._client()
        c._requested_model = 'auto'
        p = c._build_payload('hello', 'UTC')
        self.assertEqual(p['model'], 'auto')
        self.assertEqual(p['parent_message_id'], 'client-created-root')
        self.assertNotIn('conversation_id', p)
        self.assertNotIn('tools', p)

    def test_requested_model_injected(self):
        c = self._client()
        c._requested_model = 'gpt-5-5'
        p = c._build_payload('hello', 'UTC')
        self.assertEqual(p['model'], 'gpt-5-5')

    def test_followup_includes_ids(self):
        c = self._client()
        c.data['conversation_id'] = 'conv-9'
        c.data['parent_message_id'] = 'parent-9'
        p = c._build_payload('hello', 'UTC', parent_message_id='parent-9')
        self.assertEqual(p['conversation_id'], 'conv-9')
        self.assertEqual(p['parent_message_id'], 'parent-9')

    def test_tools_attached(self):
        c = self._client()
        p = c._build_payload('hello', 'UTC', tools=[{'type': 'function', 'function': {'name': 'f'}}])
        self.assertEqual(p['tools'], [{'type': 'function', 'function': {'name': 'f'}}])

    def test_chat_params_merged(self):
        c = self._client()
        c.chat_params = {'temperature': 0.7, 'max_tokens': 100}
        p = c._build_payload('hello', 'UTC')
        self.assertEqual(p['temperature'], 0.7)
        self.assertEqual(p['max_tokens'], 100)


if __name__ == '__main__':
    unittest.main()
