import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sage import entries
from sage.cli import parser, run
from sage.storage import read, save
from test_sage import FakeAPI
IDEA = dict(id='e0001', title='Test', category='Basics', scope='Overview')


class BoundedTests(unittest.TestCase):
    def test_build_skips_failure_exports_and_can_explicitly_retry(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), patch('sage.cli.API', FakeAPI):
            p = Path(tmp)
            def command(*args):
                run(parser().parse_args(list(args)))
            command('init', tmp, '--subject', 'Test', '--count', '2')
            save(p / 'ideas.json', [IDEA, dict(IDEA, id='e0002', title='Second')])
            original = entries.generate
            calls = []
            def generate(api, project, config, idea):
                calls.append(idea['id'])
                if idea['id'] == 'e0001':
                    raise entries.EntryFailure(['Unsupported'], p / 'reviews/e0001.json')
                return original(api, project, config, idea)
            with patch('sage.cli.entries.generate', side_effect=generate):
                command('build', tmp)
                self.assertEqual(calls, ['e0001', 'e0002'])
                command('build', tmp)
                self.assertEqual(calls, ['e0001', 'e0002'])
            self.assertTrue(read(p / 'errors/e0001.json')['skipped'])
            self.assertEqual((p / 'encyclopedia.html').read_text().count('<article '), 1)
            self.assertFalse((p / 'preface.json').exists())
            command('generate', tmp, '--entry', 'e0001')
            self.assertFalse((p / 'errors/e0001.json').exists())
            command('build', tmp)
            self.assertNotIn('PARTIAL DRAFT', (p / 'encyclopedia.html').read_text())
            self.assertTrue((p / 'preface.json').exists())
