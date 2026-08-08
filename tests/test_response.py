import unittest

from engine.response import (
    build_chat_response,
    build_stream_chunk,
    build_model_list,
)


class TestBuildChatResponse(unittest.TestCase):

    def test_standard_shape(self):
        body = build_chat_response(
            {'text': 'hello', 'model': 'gpt-x', 'finish_reason': 'stop'},
            'user: hi',
            'gpt-x',
        )
        self.assertEqual(body['object'], 'chat.completion')
        self.assertTrue(body['id'].startswith('chatcmpl-'))
        self.assertIsInstance(body['created'], int)
        self.assertEqual(body['model'], 'gpt-x')
        choice = body['choices'][0]
        self.assertEqual(choice['index'], 0)
        self.assertEqual(choice['message']['role'], 'assistant')
        self.assertEqual(choice['message']['content'], 'hello')
        self.assertEqual(choice['finish_reason'], 'stop')
        self.assertIn('prompt_tokens', body['usage'])
        self.assertIn('completion_tokens', body['usage'])
        self.assertIn('total_tokens', body['usage'])
        self.assertTrue(body['system_fingerprint'].startswith('fp_'))

    def test_reasoning(self):
        body = build_chat_response(
            {'text': 'answer', 'reasoning': 'think', 'model': 'gpt-x'},
            '',
            'gpt-x',
        )
        self.assertEqual(body['choices'][0]['message']['reasoning_content'], 'think')
        self.assertEqual(body['usage']['completion_tokens_details'],
                         {'reasoning_tokens': body['usage']['completion_tokens_details']['reasoning_tokens']})
        self.assertIn('reasoning_tokens', body['usage']['completion_tokens_details'])

    def test_tool_calls_null_content(self):
        body = build_chat_response(
            {'text': '', 'model': 'gpt-x', 'finish_reason': 'tool_calls',
             'tool_calls': [{'id': 'call_1', 'type': 'function'}]},
            '',
            'gpt-x',
        )
        self.assertIsNone(body['choices'][0]['message']['content'])
        self.assertEqual(body['choices'][0]['message']['tool_calls'],
                         [{'id': 'call_1', 'type': 'function'}])
        self.assertEqual(body['choices'][0]['finish_reason'], 'tool_calls')

    def test_extended(self):
        body = build_chat_response(
            {'text': 'x', 'model': 'gpt-x', 'conversation_id': 'c1',
             'parent_message_id': 'p1', 'rate_limits': {'a': 1}},
            '',
            'gpt-x',
            extended=True,
        )
        self.assertEqual(body['conversation_id'], 'c1')
        self.assertEqual(body['parent_message_id'], 'p1')
        self.assertEqual(body['rate_limits'], {'a': 1})


class TestBuildStreamChunk(unittest.TestCase):
    def test_basic(self):
        c = build_stream_chunk('chatcmpl-1', 123, 'gpt-x', {'content': 'a'})
        self.assertEqual(c['object'], 'chat.completion.chunk')
        self.assertIsNone(c['choices'][0]['finish_reason'])
        self.assertNotIn('usage', c)

    def test_stop(self):
        c = build_stream_chunk('chatcmpl-1', 123, 'gpt-x', {}, 'stop')
        self.assertEqual(c['choices'][0]['finish_reason'], 'stop')

    def test_usage_optional(self):
        c = build_stream_chunk('chatcmpl-1', 123, 'gpt-x', {}, 'stop',
                               usage={'prompt_tokens': 1, 'completion_tokens': 2, 'total_tokens': 3})
        self.assertEqual(c['usage']['total_tokens'], 3)


class TestBuildModelList(unittest.TestCase):
    def test_guards_null_product_features(self):
        raw = [
            {'slug': 'gpt-a', 'title': 'GPT A', 'description': 'd',
             'max_tokens': 100, 'reasoning_type': None, 'product_features': None},
        ]
        out = build_model_list(raw)
        self.assertEqual(out['object'], 'list')
        self.assertEqual(out['data'][0]['id'], 'gpt-a')
        self.assertEqual(out['data'][0]['info']['abilities']['vision'], 0)
        self.assertEqual(out['data'][0]['info']['abilities']['thinking'], 0)

    def test_abilities(self):
        raw = [
            {'slug': 'gpt-b', 'title': 'GPT B', 'product_features': {
                'attachments': {'image_mime_types': ['image/png'], 'accepted_mime_types': ['txt']},
            }, 'reasoning_type': 'thinking'},
        ]
        out = build_model_list(raw)
        m = out['data'][0]
        self.assertEqual(m['info']['abilities'], {'vision': 1, 'document': 1, 'thinking': 1})
        self.assertEqual(m['owned_by'], 'openai')


if __name__ == '__main__':
    unittest.main()
