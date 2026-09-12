import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sage.api import API
from sage.cli import parser, run
from sage.menu import choose_model, menu
from sage.models import DEFAULT_MODEL
from sage.storage import read
from test_sage import FakeAPI


class ModelTests(unittest.TestCase):
    def test_defaults_and_overrides(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test'}, clear=True):
            self.assertEqual(API().model, DEFAULT_MODEL)
            self.assertEqual(parser().parse_args(['init', 'p', '--subject', 'Test']).model, DEFAULT_MODEL)
        with patch.dict('os.environ', {'OPENAI_MODEL': 'gpt-5.6-terra', 'OPENAI_API_KEY': 'test'}):
            self.assertEqual(API().model, 'gpt-5.6-terra')
            self.assertEqual(API('gpt-5.6-sol').model, 'gpt-5.6-sol')
            args = parser().parse_args(['init', 'p', '--subject', 'Test', '--model', DEFAULT_MODEL])
            self.assertEqual(args.model, DEFAULT_MODEL)

    def test_picker(self):
        for answers, expected in [([''], DEFAULT_MODEL), (['2'], 'gpt-5.6-terra'),
                                  (['5', 'custom-model'], 'custom-model'),
                                  (['99', 'bad id', '3'], 'gpt-5.6-sol')]:
            with patch('builtins.input', side_effect=answers), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(choose_model(DEFAULT_MODEL), expected)

    def test_menu_switch_persists_and_is_used_for_inference(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            project = Path(tmp) / 'project'
            run(parser().parse_args(['init', str(project), '--subject', 'Test', '--count', '1']))
            before = read(project / 'config.json')
            with patch('builtins.input', side_effect=['2', str(project), '9', '2', '0']):
                menu()
            after = read(project / 'config.json')
            self.assertEqual(after, dict(before, model='gpt-5.6-terra'))
            with patch('sage.cli.API', side_effect=FakeAPI) as client:
                run(parser().parse_args(['ideas', str(project)]))
                self.assertEqual(client.call_args.args[0], 'gpt-5.6-terra')
            with self.assertRaises(ValueError):
                run(parser().parse_args(['model', str(project), '--model', ' ']))
            self.assertEqual(read(project / 'config.json'), after)
