import unittest
from html.parser import HTMLParser
from sage import book
from sage.citations import Chicago, canonical_url

class ChicagoTests(unittest.TestCase):
    def article(self):
        return dict(id='e0001', title='A: <Title>', category='Test', generated_at='2026-09-12',
                    paragraphs=[dict(text='First paragraph [1, 2]', source_ids=[1, 2]),
                                dict(text='Second paragraph', source_ids=[1])],
                    sources=[dict(id=1, title='A source', url='https://example.org/a?utm_source=openai'),
                             dict(id=2, title='Other source', url='https://example.org/b')])

    def test_notes_bibliography_and_escaping(self):
        report=[]
        output=book.render(dict(subject='Test'), [self.article()], partial=True,
                           citation_style='chicago', citation_report=report)
        self.assertIn('--paper:#ffffff', output)
        self.assertIn('id="note-1"', output)
        self.assertIn('id="note-2"', output)
        self.assertIn('href="#note-2"', output)
        self.assertEqual(output.count('class="bibliography-entry"'), 2)
        self.assertNotIn('First paragraph [1, 2]', output)
        self.assertNotIn('utm_source', output)
        self.assertIn('A: &lt;Title&gt;', output)
        self.assertEqual(len(report), 2)
        self.assertEqual(report[0]['entries'], ['e0001'])

    def test_explicit_bibliographic_overrides(self):
        c=Chicago({'https://example.org/a':dict(note='Jane Doe, Book (Press, 2020), 4.',
                 bibliography='Doe, Jane. Book. Press, 2020. <script>')})
        c.paragraphs(self.article())
        output=c.render()
        self.assertIn('Jane Doe, Book (Press, 2020), 4.', output)
        self.assertIn('&lt;script&gt;', output)
        self.assertEqual(len(c.report()), 1)

    def test_tracking_only_removed(self):
        self.assertEqual(canonical_url('https://example.org/a?id=2&utm_source=x#page3'),
                         'https://example.org/a?id=2#page3')
