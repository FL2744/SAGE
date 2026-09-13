import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from sage.citation_research import enrich
from sage.storage import read

class ReferenceTests(unittest.TestCase):
    def articles(self):
        return [dict(paragraphs=[dict(source_ids=[1, 2])], sources=[
            dict(id=1, title='First', url='https://example.org/a?utm_source=x'),
            dict(id=2, title='First', url='https://example.org/a')])]

    def test_cached_authorless_source_and_manual_override(self):
        result=dict(verified=True,author='',bibliography_author='',title='First',site='Example',date='',
                    note='“First,” Example, https://example.org/a.',
                    bibliography='Example. “First.” https://example.org/a.',
                    evidence_urls=['https://example.org/a'],explanation='No byline on the source.')
        api=Mock();api.call.return_value=(result,[]);client=Mock(return_value=api)
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            overrides=enrich(client,Path(tmp),self.articles(),{})
            self.assertIn('https://example.org/a',overrides)
            api.call.assert_called_once()
            self.assertTrue(api.call.call_args.kwargs['search'])
            client.reset_mock()
            overrides=enrich(client,Path(tmp),self.articles(),{'https://example.org/a':{'note':'Manual note'}})
            client.assert_not_called()
            self.assertEqual(overrides['https://example.org/a']['note'],'Manual note')

    def test_failed_lookup_not_used_or_repeated(self):
        api=Mock();api.call.return_value=(dict(verified=True,title='Guess',note='Guess',bibliography='Guess',evidence_urls=[]),[])
        client=Mock(return_value=api)
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(enrich(client,Path(tmp),self.articles(),{}),{})
            self.assertFalse(read(Path(tmp)/'citation-cache.json')['https://example.org/a']['verified'])
            enrich(client,Path(tmp),self.articles(),{})
            api.call.assert_called_once()

    def test_offline_and_manual_require_no_key(self):
        client=Mock(side_effect=AssertionError('No API'))
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            enrich(client,Path(tmp),self.articles(),{},limit=0)
            enrich(client,Path(tmp),self.articles(),{'https://example.org/a':dict(note='Manual',bibliography='Manual')})
            client.assert_not_called()
