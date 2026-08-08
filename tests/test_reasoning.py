import unittest

import engine.session


class TestReasoningExtraction(unittest.TestCase):

    def setUp(self):
        self.engine = engine.session.ChatGPT.__new__(engine.session.ChatGPT)

    def test_no_reasoning_when_text_has_indented_code(self):
        # Real guest-backend reply (captured live): one continuous text whose
        # FIRST occurrence of "  " is the 4-space indent of the Rust sample.
        text = ('Olá! 😊\n\n**Rust** é uma linguagem...\n\n```rust\n'
                'fn main() {\n    let nome = "Rust";\n    println!("Olá, {}!", nome);\n'
                '}\n```\n\nO compilador traduz isso...')
        out, reasoning = self.engine._extract_reasoning(text)
        self.assertEqual(out, text)
        self.assertEqual(reasoning, '')

    def test_no_double_space(self):
        text = 'Resposta simples, sem raciocínio separado.'
        out, reasoning = self.engine._extract_reasoning(text)
        self.assertEqual(out, text)
        self.assertEqual(reasoning, '')

    def test_double_space_at_start_does_not_swallow_text(self):
        text = '  intencional: espaço duplo no início.'
        out, reasoning = self.engine._extract_reasoning(text)
        self.assertEqual(out, text)
        self.assertEqual(reasoning, '')


if __name__ == '__main__':
    unittest.main()
