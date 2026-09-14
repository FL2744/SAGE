import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_chicago
from sage import book
from sage.menu import menu
from sage.storage import save

class EditionTests(unittest.TestCase):
    def test_layouts(self):
        article=test_chicago.ChicagoTests().article()
        for edition in ('web','kindle','no-references','chicago'):
            text=book.render(dict(subject='Test'),[article],partial=True,edition=edition)
            self.assertIn('href="#e0001"',text)
            if edition in ('kindle','no-references'):
                self.assertNotIn('columns:2',text)
            if edition=='no-references':
                self.assertNotIn('<span class="toc-theme">',text)
                self.assertIn('padding-left:0;margin-left:0;list-style-position:inside',text)
                self.assertNotIn('<h3>Sources',text)
            if edition=='kindle':self.assertIn('<h3>Sources',text)
            if edition=='web':self.assertIn('columns:2',text)

    def test_menu_routes_all_four_editions(self):
        with tempfile.TemporaryDirectory() as tmp:
            save(Path(tmp)/'config.json',dict(subject='Test',model='test'))
            for choice,edition in enumerate(('web','kindle','no-references','chicago'),1):
                answers=['2',tmp,'7',str(choice)]+(['n'] if choice==4 else [])+['','','0']
                with patch('builtins.input',side_effect=answers),patch('sage.cli.run') as run,contextlib.redirect_stdout(io.StringIO()):
                    menu()
                self.assertEqual(run.call_args.args[0].edition,edition)
                self.assertTrue(run.call_args.args[0].partial)

    def test_cli_partial_defaults_and_complete_override(self):
        from sage.cli import parser
        for edition in ('web','kindle','no-references','chicago'):
            args=['export','project','--edition',edition]
            self.assertTrue(parser().parse_args(args).partial)
            self.assertFalse(parser().parse_args(args+['--complete']).partial)

    def test_kindle_has_only_superscript_citations(self):
        import re
        article=test_chicago.ChicagoTests().article()
        article['paragraphs'][0]['text']='Text [1][2] [1, 2] (Sources: 1, 2).'
        original=article['paragraphs'][0]['text']
        output=book.render(dict(subject='Test'),[article],partial=True,edition='kindle')
        self.assertIn('<p>Text. <sup>', output)
        self.assertIn('href="#e0001-source-1"', output)
        self.assertIn('id="e0001-source-1"', output)
        without_superscripts=re.sub(r'<sup>.*?</sup>', '', output)
        self.assertNotIn('[1]', without_superscripts)
        self.assertNotIn('[1, 2]', without_superscripts)
        self.assertEqual(article['paragraphs'][0]['text'], original)

    def test_kindle_omits_publication_metadata(self):
        article=test_chicago.ChicagoTests().article()
        for mode in ('standard','strict'):
            article['generation_mode']=mode
            output=book.render(dict(subject='Test'),[article],partial=True,edition='kindle')
            for text in ('Generated 2026', 'AI fact-check skipped', 'Automated evidence review passed',
                         'Written for the educated layperson', 'PARTIAL DRAFT', '<footer>'):
                self.assertNotIn(text,output)
            self.assertIn('<h3>Sources</h3>',output)
            self.assertIn('href="#e0001-source-1"',output)
        web=book.render(dict(subject='Test'),[article],partial=True,edition='web')
        self.assertNotIn('PARTIAL DRAFT',web)
        self.assertNotIn('<footer>',web)

    def test_default_web_cleans_citations_and_metadata(self):
        import re
        article=test_chicago.ChicagoTests().article()
        article['paragraphs'][0]['text']='Example [1][2] [1, 2] (Sources: 1, 2).'
        for edition in (None,'web'):
            output=book.render(dict(subject='Test'),[article],partial=True,edition=edition)
            self.assertIn('<p>Example. <sup>',output)
            self.assertIn('href="#e0001-source-1"',output)
            self.assertIn('id="e0001-source-1"',output)
            self.assertNotIn('[1]',re.sub(r'<sup>.*?</sup>','',output))
            for text in ('Written for the educated layperson','PARTIAL DRAFT','<footer>','Generated 2026'):
                self.assertNotIn(text,output)

    def test_titles_only_in_all_contents(self):
        import re
        article=test_chicago.ChicagoTests().article()
        article['category']='Neural Networks and Deep Learning'
        for edition in ('web','kindle','no-references','chicago'):
            output=book.render(dict(subject='Test'),[article],partial=True,edition=edition)
            toc=re.search(r'<nav id="contents".*?</nav>',output,re.S).group()
            self.assertNotIn(article['category'],toc)
            self.assertNotIn('<small>',toc)
            self.assertNotIn('toc-theme',toc)
            self.assertIn('href="#e0001"',toc)
            self.assertIn('A: &lt;Title&gt;',toc)
