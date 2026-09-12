import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sage import entries
from sage.cli import parser, run
from sage.storage import read
from test_sage import FakeAPI

CONFIG = dict(subject='Test', guidance='', domains=['example.edu'], min_words=500, max_words=800)
IDEA = dict(id='e0001', title='Test', category='Basics', scope='Overview')


class RetryAPI(FakeAPI):
    def __init__(self, always_fail=False):
        self.calls = []
        self.reviews = 0
        self.always_fail = always_fail

    def call(self, prompt, schema=None, search=False, domains=None):
        self.calls.append((prompt, schema, search, domains))
        if prompt.startswith('Repair the evidence'):
            return 'Corrected evidence with new authoritative support', [
                {'url': 'https://example.edu/a', 'title': 'Existing'},
                {'url': 'https://example.edu/new', 'title': 'New evidence'},
                {'url': 'javascript:bad', 'title': 'Unsafe'}]
        if schema is entries.REVIEW:
            self.reviews += 1
            if self.reviews == 1 or self.always_fail:
                return dict(passed=False, issues=['Need “new evidence”. ' * 100]), []
        result, cites = super().call(prompt, schema, search, domains)
        if schema is entries.ARTICLE and self.reviews:
            result['paragraphs'][0]['source_ids'] = [1, 3]
        return result, cites


class RetryTests(unittest.TestCase):
    def test_new_evidence_reaches_revised_draft(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            api = RetryAPI()
            result = entries.generate(api, Path(tmp), CONFIG, IDEA)
            self.assertEqual([s['id'] for s in result['sources']], [1, 2, 3])
            self.assertEqual(result['sources'][2]['url'], 'https://example.edu/new')
            repairs = [c for c in api.calls if c[0].startswith('Repair the evidence')]
            self.assertEqual(len(repairs), 1)
            self.assertTrue(repairs[0][2])
            self.assertEqual(repairs[0][3], CONFIG['domains'])
            self.assertIn('Need “new evidence”', repairs[0][0])
            drafts = [c[0] for c in api.calls if c[1] is entries.ARTICLE]
            self.assertIn('Corrected evidence with new authoritative support', drafts[1])
            self.assertIn('https://example.edu/new', drafts[1])
            self.assertEqual(len(read(Path(tmp) / 'research/e0001.json')['corrections']), 1)

    def test_bounded_failure_has_full_files_and_short_terminal_message(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            def command(*argv):
                run(parser().parse_args(list(argv)))
            command('init', tmp, '--subject', 'Test', '--count', '1')
            with patch('sage.cli.API', FakeAPI):
                command('ideas', tmp)
            api = RetryAPI(always_fail=True)
            output = io.StringIO()
            with patch('sage.cli.API', return_value=api), contextlib.redirect_stderr(output):
                command('generate', tmp)
            self.assertEqual(api.reviews, 3)
            self.assertEqual(sum(c[0].startswith('Repair the evidence') for c in api.calls), 2)
            self.assertLess(len(output.getvalue()), 400)
            self.assertNotIn('Need', output.getvalue())
            report = read(Path(tmp) / 'reviews/e0001.json')
            error = read(Path(tmp) / 'errors/e0001.json')
            self.assertEqual(error['issues'], report['review']['issues'])
            self.assertGreater(len(error['issues'][0]), 1000)
            self.assertFalse((Path(tmp) / 'entries/e0001.json').exists())

    def test_validation_retry_does_not_research(self):
        class ShortAPI(FakeAPI):
            def call(self, prompt, schema=None, **kwargs):
                if schema is entries.ARTICLE:
                    return dict(paragraphs=[dict(text='Too short', source_ids=[1, 2])], summary='Short'), []
                if prompt.startswith('Repair'):
                    raise AssertionError('Should not research a length issue')
                return super().call(prompt, schema, **kwargs)
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(entries.EntryFailure) as failure:
                entries.generate(ShortAPI(), Path(tmp), CONFIG, IDEA)
            self.assertIn('words', failure.exception.issues[0])
            self.assertIn('validation_issues', read(Path(tmp) / 'reviews/e0001.json'))
