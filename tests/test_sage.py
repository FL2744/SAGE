import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sage import book, entries, ideas
from sage.cli import parser, run
from sage.storage import read, save
from sage.api import API


class FakeAPI:
    model = 'test-model'
    def __init__(self, *args):
        pass
    def call(self, prompt, schema=None, search=False, domains=None):
        if schema and 'ideas' in schema['properties']:
            return {'ideas': [{'title': 'Atoms', 'category': 'Basics', 'scope': 'Atomic structure'}]}, []
        if schema and 'source_ids' in json.dumps(schema):
            return {'paragraphs': [{'text': ' '.join(['matter'] * 550), 'source_ids': [1, 2]}], 'summary': 'The entry covers matter.'}, []
        if schema and 'passed' in schema['properties']:
            return {'passed': True, 'issues': []}, []
        if schema:
            return {'paragraphs': ['This volume explores matter.']}, []
        return 'Evidence brief', [{'url': 'https://example.edu/a', 'title': 'Source A'}, {'url': 'https://example.org/b', 'title': 'Source B'}]


class Tests(unittest.TestCase):
    def test_complete_workflow_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp, patch('sage.cli.API', FakeAPI):
            p = str(Path(tmp) / 'project')
            run(parser().parse_args(['init', p, '--subject', 'Chemistry', '--count', '1']))
            run(parser().parse_args(['build', p]))
            project = Path(p)
            original = (project / 'entries/e0001.json').read_text()
            run(parser().parse_args(['build', p]))
            self.assertEqual(original, (project / 'entries/e0001.json').read_text())
            output = (project / 'encyclopedia.html').read_text()
            self.assertIn('href="#e0001"', output)
            self.assertIn('id="e0001"', output)
            self.assertIn('href="#e0001-source-1"', output)
            self.assertIn('id="preface"', output)
            article = read(project / 'entries/e0001.json')
            article['summary'] = 'Changed'
            save(project / 'entries/e0001.json', article)
            with self.assertRaisesRegex(ValueError, 'stale'):
                run(parser().parse_args(['export', p]))

    def test_validation(self):
        cfg = dict(min_words=500, max_words=800)
        src = [dict(id=1), dict(id=2)]
        a = dict(paragraphs=[dict(text='word ' * 499, source_ids=[1, 2])], summary='Summary')
        with self.assertRaisesRegex(ValueError, '499 words'):
            entries.validate(a, src, cfg)
        a['paragraphs'][0]['text'] = 'word ' * 500
        entries.validate(a, src, cfg)
        a['paragraphs'][0]['source_ids'] = [99]
        with self.assertRaises(ValueError):
            entries.validate(a, src, cfg)

    def test_rejected_review_never_returns_entry(self):
        class RejectAPI(FakeAPI):
            def call(self, prompt, schema=None, **kw):
                if schema and 'passed' in schema['properties']:
                    return dict(passed=False, issues=['Unsupported assertion']), []
                return super().call(prompt, schema, **kw)
        with tempfile.TemporaryDirectory() as tmp:
            config = dict(subject='Test', guidance='', domains=[], min_words=500, max_words=800)
            with self.assertRaisesRegex(ValueError, 'retry limit'):
                entries.generate(RejectAPI(), Path(tmp), config, dict(id='e0001', title='Test'))
            self.assertTrue((Path(tmp) / 'reviews/e0001.json').exists())
            self.assertFalse((Path(tmp) / 'entries/e0001.json').exists())

    def test_html_escaping(self):
        article = dict(id='e0001', title='<script>alert(1)</script>', category='A&B',
                       paragraphs=[dict(text='<img src=x onerror=bad>', source_ids=[1])],
                       sources=[dict(id=1, url='javascript:alert(1)', title='bad')], generated_at='2026-09-11')
        output = book.render(dict(subject='<Test>'), [article], partial=True)
        self.assertNotIn('<script>', output)
        self.assertNotIn('javascript:', output)
        self.assertIn('&lt;img', output)
        self.assertIn('PARTIAL DRAFT', output)

    def test_idea_deduplication_stops_stalled_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'No new distinct'):
                ideas.generate(FakeAPI(), Path(tmp), dict(count=2))
            self.assertEqual(len(read(Path(tmp) / 'ideas.json')), 1)

    def test_api_payload(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass
            def read(self):
                return json.dumps(dict(status='completed', output=[dict(content=[dict(type='output_text', text='{"ok":true}', annotations=[])])])).encode()
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test'}), patch('urllib.request.urlopen', return_value=Response()) as send:
            result, _ = API().call('Test', {'type': 'object'}, True, ['example.edu'])
            payload = json.loads(send.call_args[0][0].data)
            self.assertFalse(payload['store'])
            self.assertEqual(payload['tools'][0]['filters']['allowed_domains'], ['example.edu'])
            self.assertEqual(payload['text']['format']['type'], 'json_schema')
            self.assertTrue(result['ok'])


if __name__ == '__main__':
    unittest.main()
