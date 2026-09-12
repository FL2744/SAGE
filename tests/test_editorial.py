import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from sage import entries
from sage.storage import read
from test_sage import FakeAPI
from test_research_retry import CONFIG, IDEA


class EditorialTests(unittest.TestCase):
    def test_suggestions_do_not_retry(self):
        class SuggestionsAPI(FakeAPI):
            calls = 0
            def call(self, prompt, schema=None, **kwargs):
                self.calls += 1
                if schema is entries.REVIEW:
                    return dict(passed=False, issues=[], suggestions=['Prefer a shorter opening.'],
                                affected_paragraphs=[], summary_needs_revision=False), []
                return super().call(prompt, schema, **kwargs)
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            api = SuggestionsAPI()
            article = entries.generate(api, Path(tmp), CONFIG, IDEA)
            self.assertEqual(api.calls, 3)
            self.assertTrue(article['review']['passed'])
            self.assertEqual(read(Path(tmp) / 'reviews/e0001.json')['review']['suggestions'],
                             ['Prefer a shorter opening.'])

    def test_revision_preserves_cleared_text_and_blocks_despite_passed_flag(self):
        class TargetAPI(FakeAPI):
            drafts = 0
            reviews = 0
            def call(self, prompt, schema=None, **kwargs):
                if schema is entries.ARTICLE:
                    self.drafts += 1
                    return dict(paragraphs=[
                        dict(text=('original ' if self.drafts == 1 else 'corrected ') * 275, source_ids=[1]),
                        dict(text=('preserve ' if self.drafts == 1 else 'unwanted ') * 275, source_ids=[2])],
                        summary='Original synopsis' if self.drafts == 1 else 'Unwanted synopsis'), []
                if schema is entries.REVIEW:
                    self.reviews += 1
                    return dict(passed=True, issues=['Fix paragraph 1'] if self.reviews == 1 else [],
                                suggestions=['Optional context'], affected_paragraphs=[1] if self.reviews == 1 else [],
                                summary_needs_revision=False), []
                return super().call(prompt, schema, **kwargs)
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            api = TargetAPI()
            article = entries.generate(api, Path(tmp), CONFIG, IDEA)
            self.assertEqual(api.drafts, 2)
            self.assertEqual(article['paragraphs'][0]['text'], 'corrected ' * 275)
            self.assertEqual(article['paragraphs'][1]['text'], 'preserve ' * 275)
            self.assertEqual(article['summary'], 'Original synopsis')

    def test_revision_rejects_changed_structure(self):
        old = dict(paragraphs=[dict(text='Original', source_ids=[1])], summary='Original')
        with self.assertRaisesRegex(ValueError, 'paragraph count'):
            entries.preserve_unflagged(old, dict(paragraphs=[], summary=''),
                                      dict(affected_paragraphs=[1], summary_needs_revision=False))
