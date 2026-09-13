"""Offline Chicago notes/bibliography export from saved citation metadata.

Optional citation overrides are keyed by URL in the project's citations.json.
Never infer personal authors, publication dates, or publisher names from URLs.
"""
import html
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from .entries import safe_url


def canonical_url(url):
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith('utm_')]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def paragraph_text(paragraph):
    # Some generated paragraphs repeat the structured citations as trailing [1, 2].
    text = paragraph['text']
    pattern = r'\s*\[([0-9]+(?:\s*,\s*[0-9]+)*)\]\s*$'
    while True:
        match = re.search(pattern, text)
        if not match or not set(map(int, match.group(1).split(','))).issubset(paragraph['source_ids']):
            return text
        text = text[:match.start()].rstrip()


def citation(source, bibliography=False):
    override = source.get('bibliography' if bibliography else 'note')
    if override:
        return html.escape(override)
    title = ' '.join(source.get('title', '').split()) or 'Untitled web resource'
    author = source.get('bibliography_author' if bibliography else 'author', '')
    if bibliography and not author:
        author = source.get('author', '')
    site = source.get('site', '')
    date = source.get('date', '')
    accessed = source.get('accessed', '')
    url = canonical_url(source['url'])
    esc = html.escape
    link = '<a href="%s">%s</a>' % (esc(url, quote=True), esc(url))
    if bibliography:
        parts = ([esc(author) + '.'] if author else []) + ['“' + esc(title.rstrip('.')) + '.”']
        if site:
            parts.append(esc(site) + '.')
        if date:
            parts.append(esc(date) + '.')
        elif accessed:
            parts.append('Accessed ' + esc(accessed) + '.')
        return ' '.join(parts + [link + '.'])
    parts = ([esc(author)] if author else []) + ['“' + esc(title) + '”']
    if site:
        parts.append(esc(site))
    if date:
        parts.append(esc(date))
    elif accessed:
        parts.append('accessed ' + esc(accessed))
    return ', '.join(parts + [link]) + '.'


class Chicago:
    def __init__(self, overrides=None):
        self.overrides = {canonical_url(k): v for k, v in (overrides or {}).items()}
        self.notes = []
        self.sources = {}
        self.incomplete = {}

    def paragraphs(self, entry):
        sources = {s['id']: s for s in entry['sources']}
        paragraphs = []
        for paragraph in entry['paragraphs']:
            citations = []
            for ident in dict.fromkeys(paragraph['source_ids']):
                original = sources[ident]
                if not safe_url(original['url']):
                    continue
                url = canonical_url(original['url'])
                source = dict(original, **self.overrides.get(url, {}))
                source['url'] = url
                self.sources[url] = source
                citations.append(citation(source).rstrip('.'))
                if not (source.get('note') and source.get('bibliography')):
                    missing = [field for field in ('author', 'site', 'date') if not source.get(field)]
                    self.incomplete.setdefault(url, dict(title=source.get('title', ''), url=url,
                        missing=missing, entries=[]))['entries'].append(entry['id'])
            if not citations:
                raise ValueError('No usable citations for a paragraph in ' + entry['id'])
            number = len(self.notes) + 1
            self.notes.append('<li id="note-%d">%s. <a class="backlink" href="#ref-%d">↩</a></li>' %
                              (number, '; '.join(citations), number))
            paragraphs.append('<p>%s<sup><a id="ref-%d" href="#note-%d" aria-label="Note %d">%d</a></sup></p>' %
                              (html.escape(paragraph_text(paragraph)), number, number, number, number))
        return ''.join(paragraphs)

    def render(self):
        sources = sorted(self.sources.values(), key=lambda s:
                         (s.get('bibliography_author') or s.get('author') or s.get('title', '')).casefold())
        return '<section id="notes"><h2>Notes</h2><ol>%s</ol></section><section id="bibliography"><h2>Bibliography</h2>%s</section>' % (
            ''.join(self.notes), ''.join('<p class="bibliography-entry">%s</p>' % citation(s, True) for s in sources))

    def report(self):
        return [dict(item, entries=sorted(set(item['entries']))) for item in self.incomplete.values()]


def without_citations(text):
    """Remove generated citation notation without changing ordinary prose/numbers."""
    # Generated source labels can occur anywhere, in parentheses or brackets.
    # Match only labels/IDs, never explanatory prose such as (sources of income).
    label = r'(?:sources?|references?)(?:\s+IDs?)?\s*:?\s*'
    body = label + r'\d+(?:\s*(?:[,;–-]|and)\s*(?:' + label + r')?\d+)*'
    text = re.sub(r'\s*(?:\(\s*' + body + r'\s*\)|\[\s*' + body + r'\s*\])', '', text, flags=re.I)
    # Numeric Markdown citation links, footnote references and citation groups.
    text = re.sub(r'\[(?:\^)?\d+(?:\s*[,;–-]\s*\d+)*\]\(https?://[^\s)]+\)', '', text)
    text = re.sub(r'\s*\[(?:\^)?\d+(?:\s*[,;–-]\s*\d+)*\]', '', text)
    text = re.sub(r'cite.*?', '', text)
    # Remove empty citation remnants, including nested punctuation-only groups.
    while re.search(r'\([\s,;:،؛.]*\)', text):
        text = re.sub(r'\([\s,;:،؛.]*\)', '', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return re.sub(r' +([,.;:!?])', r'\1', text).strip()
