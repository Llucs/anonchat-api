import unittest

from engine.text import TextAssembler


class TestTextAssembler(unittest.TestCase):

    def test_initial_append(self):
        a = TextAssembler()
        a.absorb('hello')
        self.assertEqual(a.text(), 'hello')
        self.assertEqual(a.suffix(), 'hello')
        self.assertEqual(a.suffix(), '')

    def test_stale_full_snapshot_skipped(self):
        a = TextAssembler()
        a.absorb('hello wor', full_snapshot=True)
        a.absorb('hello wor', full_snapshot=True)
        self.assertEqual(a.text(), 'hello wor')

    def test_snapshot_supersedes(self):
        a = TextAssembler()
        a.absorb('hello', full_snapshot=True)
        a.absorb('hello world', full_snapshot=True)
        self.assertEqual(a.text(), 'hello world')

    def test_unrelated_snapshot_replaces(self):
        a = TextAssembler()
        a.absorb('first message', full_snapshot=True)
        a.absorb('replacement message', full_snapshot=True)
        self.assertEqual(a.text(), 'replacement message')

    def test_contained_delta_skipped(self):
        a = TextAssembler()
        a.absorb('hello world', full_snapshot=True)
        a.absorb('lo wo')
        self.assertEqual(a.text(), 'hello world')

    def test_delta_appended(self):
        a = TextAssembler()
        a.absorb('hel')
        a.absorb('lo')
        self.assertEqual(a.text(), 'hello')

    def test_suffix_only_new_part(self):
        a = TextAssembler()
        a.absorb('h', full_snapshot=True)
        self.assertEqual(a.suffix(), 'h')
        a.absorb('he', full_snapshot=True)
        a.absorb('l')
        self.assertEqual(a.suffix(), 'el')

    def test_empty_chunks_ignored(self):
        a = TextAssembler()
        a.absorb('')
        a.absorb(None)
        a.absorb('x')
        self.assertEqual(a.text(), 'x')


if __name__ == '__main__':
    unittest.main()
