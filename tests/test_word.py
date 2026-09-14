import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from sage import book
from sage.word import write, prepare_entries
from sage.cli import parser, run
from sage.menu import menu
from sage.storage import save
from test_chicago import ChicagoTests

try:
    import docx
except ImportError:
    docx = None

class WordTests(unittest.TestCase):
    @unittest.skipIf(docx is None, 'Install SAGE[word] for Word rendering tests')
    def test_references_links_and_contents(self):
        article = ChicagoTests().article()
        article['paragraphs'][0]['text'] = 'Example [1][2] (Sources: 1, 2).'
        other = dict(article, id='e0002', title='Zebra')
        with tempfile.TemporaryDirectory() as tmp:
            for edition in ('web', 'no-references', 'chicago'):
                output = Path(tmp) / (edition + '.docx')
                write(book.render({'subject':'Test'}, prepare_entries([other,article]),
                                  {'paragraphs':['Contribute at https://github.com/FL2744/SAGE.']},
                                  partial=True, edition=edition), output)
                with ZipFile(output) as z:
                    root=ET.fromstring(z.read('word/document.xml'))
                    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    text=''.join(root.itertext())
                    self.assertLess(text.index(article['title']), text.index('Zebra'))
                    self.assertNotIn('Sources: 1, 2', text)
                    self.assertNotIn('Back to contents', text)
                    self.assertIn('https://github.com/FL2744/SAGE', z.read('word/_rels/document.xml.rels').decode())
                    bookmarks={e.get('{'+ns['w']+'}name') for e in root.findall('.//w:bookmarkStart', ns)}
                    anchors={e.get('{'+ns['w']+'}anchor') for e in root.findall('.//w:hyperlink', ns) if e.get('{'+ns['w']+'}anchor')}
                    self.assertTrue(anchors <= bookmarks)
                    if edition=='no-references':
                        self.assertNotIn('[1]', text)
                        self.assertNotIn('Sources', text)
                    else:
                        self.assertTrue(root.findall('.//w:vertAlign[@w:val="superscript"]', ns))
                    if edition=='chicago':
                        self.assertIn('Bibliography', text)

    def test_menu_word_styles(self):
        with tempfile.TemporaryDirectory() as tmp:
            save(Path(tmp)/'config.json', {'subject':'Test','model':'test'})
            for ref, edition in [('1','web'),('2','no-references'),('3','chicago')]:
                answers=['2', tmp, '7', '5', ref]+(['n'] if ref=='3' else [])+['','','0']
                with patch('builtins.input',side_effect=answers),patch('sage.cli.run') as execute,contextlib.redirect_stdout(io.StringIO()):
                    menu()
                args=execute.call_args.args[0]
                self.assertEqual(args.format,'docx')
                self.assertEqual(args.edition,edition)
                self.assertEqual(args.output.suffix,'.docx')
                self.assertTrue(args.partial)

    @unittest.skipIf(docx is None, 'Install SAGE[word] for Word rendering tests')
    def test_cli_exports_saved_partial_without_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            a=ChicagoTests().article()
            a.update(scope='Test',summary='Test', generation_mode='standard', review={'skipped':True,'issues':[]})
            save(p/'config.json',dict(subject='Test',count=2,min_words=500,max_words=800))
            save(p/'ideas.json',[{k:a[k] for k in ('id','title','category','scope')}])
            save(p/'entries'/ 'e0001.json',a)
            with patch('sage.cli.API',side_effect=AssertionError('Export must not generate')),contextlib.redirect_stdout(io.StringIO()):
                run(parser().parse_args(['export',tmp,'--format','docx']))
            self.assertTrue((p/'encyclopedia.docx').exists())
