import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sage import ideas
from sage.cli import parser, run
from sage.menu import menu
from sage.storage import read, save
from test_sage import FakeAPI


class AddTests(unittest.TestCase):
    def command(self, *argv):
        return run(parser().parse_args(list(argv)))

    def test_extend_completed_book_through_menu(self):
        with tempfile.TemporaryDirectory() as tmp, patch('sage.cli.API', FakeAPI), contextlib.redirect_stdout(io.StringIO()):
            p = str(Path(tmp) / 'book')
            project = Path(p)
            self.command('init', p, '--subject', 'Test', '--count', '1')
            self.command('build', p)
            original = (project / 'entries/e0001.json').read_bytes()
            old_preface = read(project / 'preface.json')['fingerprint']
            old_html = (project / 'encyclopedia.html').read_bytes()
            answers = ['2', p, '10', 'Qatar', '', 'Geography, society, history', 'y',
                       'Somalia', '', 'Geography and culture', 'n', '0']
            with patch('builtins.input', side_effect=answers), patch('sage.cli.API') as api:
                menu()
                api.assert_not_called()
            self.assertEqual(read(project / 'config.json')['count'], 3)
            self.assertEqual([i['id'] for i in read(project / 'ideas.json')], ['e0001', 'e0002', 'e0003'])
            self.assertEqual((project / 'encyclopedia.html').read_bytes(), old_html)
            self.command('build', p)
            self.assertEqual((project / 'entries/e0001.json').read_bytes(), original)
            self.assertNotEqual(read(project / 'preface.json')['fingerprint'], old_preface)
            self.assertIn('Qatar', (project / 'encyclopedia.html').read_text())
            self.assertIn('Somalia', (project / 'encyclopedia.html').read_text())

    def test_validation_leaves_files_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            self.command('init', tmp, '--subject', 'Test', '--count', '1')
            self.command('add', tmp, '--title', 'Qatar', '--category', 'Countries', '--scope', 'Overview')
            project = Path(tmp)
            before = [(project / name).read_bytes() for name in ('config.json', 'ideas.json')]
            for title in ('  QATAR  ', ' '):
                with self.assertRaises(ValueError):
                    self.command('add', tmp, '--title', title, '--category', 'Countries', '--scope', 'Overview')
            self.assertEqual(before, [(project / name).read_bytes() for name in ('config.json', 'ideas.json')])

    def test_ids_and_remaining_idea_slots(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            project = Path(tmp)
            self.command('init', tmp, '--subject', 'Test', '--count', '2')
            save(project / 'ideas.json', [dict(id='e0010', title='Qatar', category='Countries', scope='Overview')])
            save(project / 'entries/e0012.json', {})
            self.command('add', tmp, '--title', 'Somalia', '--category', 'Countries', '--scope', 'Overview')
            self.assertEqual(read(project / 'ideas.json')[-1]['id'], 'e0013')
            self.assertEqual(read(project / 'config.json')['count'], 3)
            planned = ideas.generate(FakeAPI(), project, read(project / 'config.json'))
            self.assertEqual(planned[-1]['id'], 'e0014')

    def test_interrupted_update_is_recovered(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            project = Path(tmp)
            self.command('init', tmp, '--subject', 'Test', '--count', '1')
            def interrupted(path, data):
                if path.name == 'config.json':
                    raise OSError('Simulated interrupted write')
                save(path, data)
            with patch('sage.ideas.save', side_effect=interrupted):
                with self.assertRaises(OSError):
                    self.command('add', tmp, '--title', 'Qatar', '--category', 'Countries', '--scope', 'Overview')
            self.assertTrue((project / '.pending-addition.json').exists())
            self.command('list', tmp)
            self.assertEqual(read(project / 'config.json')['count'], 2)
            self.assertEqual(len(read(project / 'ideas.json')), 1)
            self.assertFalse((project / '.pending-addition.json').exists())
