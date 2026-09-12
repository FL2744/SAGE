import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sage import entries, book
from sage.cli import parser, run, accepted, load_ideas
from test_sage import FakeAPI
from test_research_retry import CONFIG, IDEA

class StandardTests(unittest.TestCase):
    def test_two_calls_over_length_and_reload_export(self):
        class LongAPI(FakeAPI):
            calls = 0
            def call(self, prompt, schema=None, **kwargs):
                self.calls += 1
                if schema is entries.REVIEW:
                    raise AssertionError('No fact-check in standard mode')
                result, cites = super().call(prompt, schema, **kwargs)
                if schema is entries.ARTICLE:
                    result['paragraphs'][0]['text'] = 'word ' * 844
                return result, cites
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            api = LongAPI()
            config = dict(CONFIG, generation_mode='standard')
            result = entries.generate(api, Path(tmp), config, IDEA)
            self.assertEqual(api.calls, 2)
            self.assertFalse(result['review']['passed'])
            from sage.storage import save
            save(Path(tmp) / 'entries/e0001.json', result)
            self.assertEqual(len(accepted(Path(tmp), CONFIG, [IDEA])), 1)
            html = book.render(config, [result], partial=True)
            self.assertIn('AI fact-check skipped', html)
            self.assertNotIn('Automated evidence review passed', html)

    def test_missing_citations_still_bounded(self):
        class InvalidAPI(FakeAPI):
            drafts = 0
            def call(self, prompt, schema=None, **kwargs):
                result, cites = super().call(prompt, schema, **kwargs)
                if schema is entries.ARTICLE:
                    self.drafts += 1
                    result['paragraphs'][0]['source_ids'] = [999]
                return result, cites
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            api = InvalidAPI()
            with self.assertRaises(entries.EntryFailure):
                entries.generate(api, Path(tmp), dict(CONFIG, generation_mode='standard'), IDEA)
            self.assertEqual(api.drafts, 2)
