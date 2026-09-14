import copy
import unittest
from sage import book
from sage.citations import without_citations
import test_chicago

class NoReferencesTests(unittest.TestCase):
    def test_clean_export_preserves_original_and_navigation(self):
        article=test_chicago.ChicagoTests().article()
        original=copy.deepcopy(article)
        result=book.render(dict(subject='Test'),[article],partial=True,citation_style='none')
        for token in ('<sup>', '<h3>Sources</h3>', 'id="notes"', 'id="bibliography"',
                      'href="#e0001-source-', 'https://example.org', '[1, 2]'):
            self.assertNotIn(token,result)
        self.assertIn('First paragraph</p>',result)
        self.assertIn('href="#e0001"',result)
        self.assertNotIn('href="#contents"',result)
        self.assertEqual(article,original)
        self.assertIn('<h3>Sources</h3>',book.render(dict(subject='Test'),[article]))

    def test_inline_notation(self):
        self.assertEqual(without_citations('Founded in 1977 [1], population 1.2 million.[2–4]'),
                         'Founded in 1977, population 1.2 million.')
        self.assertEqual(without_citations('Text [1](https://example.org). More[^2].'), 'Text. More.')

    def test_source_labels_and_ordinary_parentheses(self):
        for marker in ('(Sources: 1, 5)', '[Source IDs: 1, 2]', '[Source 1; Source 2]',
                       '[Sources 1,2]', '(Reference: 1)'):
            self.assertEqual(without_citations('Text ' + marker + '.'), 'Text.')
        text = 'Trade (sources of income) increased (in 1977).'
        self.assertEqual(without_citations(text), text)

    def test_no_publication_status_or_generation_metadata(self):
        article=test_chicago.ChicagoTests().article()
        article['generation_mode']='standard'
        result=book.render(dict(subject='Test'),[article],partial=True,citation_style='none')
        for text in ('Written for the educated layperson', 'PARTIAL DRAFT', 'Generated 2026',
                     'AI fact-check skipped', 'Back to contents', 'Created with SAGE', '<footer>'):
            self.assertNotIn(text,result)
        linked=book.render(dict(subject='Test'),[article],partial=True)
        self.assertNotIn('PARTIAL DRAFT',linked)
        self.assertIn('Back to contents',linked)
        self.assertNotIn('<footer>',linked)

    def test_empty_parentheticals(self):
        for marker in ('()', '(,)', '(,,,)', '(,,)', '(;)', '(;;)', '( , ; )', '((,))', '([1], [2])'):
            self.assertEqual(without_citations('Text ' + marker + '. Next.'), 'Text. Next.')
            self.assertEqual(without_citations('Before ' + marker + ' after.'), 'Before after.')
        self.assertEqual(without_citations('Text (in 1977; revised 1980).'), 'Text (in 1977; revised 1980).')
