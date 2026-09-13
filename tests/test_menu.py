import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sage.cli import main
from sage.menu import menu
from test_sage import FakeAPI


class MenuTests(unittest.TestCase):
    def test_default_and_explicit_launch(self):
        for argv in (["sage"], ["sage", "menu"]):
            with patch("sys.argv", argv), patch("sage.menu.menu") as launch:
                main()
                launch.assert_called_once_with()

    def test_create_build_export_and_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "volume"
            answers = ["1", "Chemistry", str(project), "invalid", "0", "1",
                       "", "", "", "", "", "3", "4", "5", "e0001", "6",
                       "7", "1", "", "n", "8", "1", "", "2", str(project), "0"]
            with patch("builtins.input", side_effect=answers), patch("sage.cli.API", FakeAPI), contextlib.redirect_stdout(io.StringIO()):
                menu()
            self.assertTrue((project / "encyclopedia.html").exists())
            self.assertTrue((project / "preface.json").exists())

    def test_errors_and_interrupts_return_to_menu(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["bad", "3", "2", "/no/such/sage-project", KeyboardInterrupt(), "0"]), contextlib.redirect_stdout(output):
            menu()
        self.assertIn("Create or open", output.getvalue())
        self.assertIn("No saved SAGE project", output.getvalue())
        self.assertIn("Returning to menu", output.getvalue())

    def test_eof_exits(self):
        with patch("builtins.input", side_effect=EOFError), contextlib.redirect_stdout(io.StringIO()):
            menu()

    def test_topics_in_domain_prompt_are_preserved_as_guidance(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'AI'
            answers = ['1', 'Artificial Intelligence', str(p), '300', '', '', '1',
                       'Focus on fundamentals.', 'Transformers, Neural Networks', 'y', '0']
            with patch('builtins.input', side_effect=answers), contextlib.redirect_stdout(io.StringIO()):
                menu()
            config = json.loads((p / 'config.json').read_text())
            self.assertEqual(config['domains'], [])
            self.assertIn('Transformers, Neural Networks', config['guidance'])
            self.assertIn('Focus on fundamentals.', config['guidance'])

    def test_long_guidance_file_and_retry(self):
        from sage.menu import ask_guidance
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'long guidance.txt'
            text=('Technical AI — attention and FFNs.\n' * 1000).strip()
            path.write_text(text,encoding='utf-8')
            with patch('builtins.input',side_effect=['@/no-such-guidance-file', '@'+str(path)]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ask_guidance(),text)
