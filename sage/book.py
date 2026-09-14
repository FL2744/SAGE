"""Preface synthesis and safe, self-contained HTML export."""
import hashlib
import html
import json
import re
from .api import obj, STRINGS
from .entries import safe_url, word_count
from .citations import Chicago, without_citations


def fingerprint(entries):
    return hashlib.sha256(json.dumps(entries, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def preface(api, config, entries):
    # Summaries come from the full accepted articles, not merely the topic list.
    summaries = [dict(title=e["title"], category=e["category"], summary=e["summary"]) for e in entries]
    result, _ = api.call(
        "Write a 600–900-word preface to an encyclopedia for educated laypeople. Synthesize the entire supplied "
        "set of entry synopses: explain scope, major themes, connections and limits. Do not introduce new factual "
        "claims or claim exhaustive coverage. In addition to the subject overview, every preface MUST include "
        "a transparent account of the production method, a reference to SAGE, the exact repository URL, and "
        "an invitation to contribute revisions and additions. Use this factual method description: SAGE stands "
        "for Synthetic Automated Generator of Encyclopedias, a Python system using large language models. "
        "User editorial guidance shapes the topic plan and intended readership. SAGE plans entries, performs "
        "web research, writes articles with source links and summaries, and assembles alphabetical exports. "
        "The current standard workflow checks citation structure but skips a separate AI fact-checking pass. "
        "Do not claim human verification, peer review, or independent fact-checking occurred unless explicitly "
        "documented. Explain that AI-assisted text may contain errors, gaps, overlaps, or outdated information. "
        "Include https://github.com/FL2744/SAGE as a plain URL so the exporter can make it clickable. "
        "Invite readers to suggest corrections, additions, better sources, clearer explanations, and updates "
        "through GitHub issues, identifying entry titles and providing proposed changes and supporting sources. "
        "Invite developers to contribute software improvements through pull requests. Balance this production "
        "and contribution account with a substantive overview drawn from the supplied synopses; adapt the "
        "overview to the encyclopedia's subject. Use plain paragraphs without markup. Subject: " + config["subject"] +
        ". All accepted entry synopses: " + json.dumps(summaries), obj(paragraphs=STRINGS))
    if not result["paragraphs"] or not all(p.strip() for p in result["paragraphs"]):
        raise ValueError("Empty preface returned.")
    return dict(**result, fingerprint=fingerprint(entries))


def preface_paragraph(text):
    """Escape prose and keep explicit web addresses clickable."""
    escaped = html.escape(text)
    def link(match):
        raw = match.group(0)
        url = raw.rstrip('.,;:!?')
        return '<a href="%s">%s</a>%s' % (url, url, raw[len(url):])
    return re.sub(r'https?://[^\s<>]+', link, escaped)


def render(config, entries, introduction=None, partial=False, citation_style="links", citation_overrides=None, citation_report=None, edition=None):
    if edition is not None:
        if edition not in ("web", "kindle", "no-references", "chicago"):
            raise ValueError("Unknown edition")
        citation_style = {"web": "links", "kindle": "links", "no-references": "none", "chicago": "chicago"}[edition]
    if citation_style not in ("links", "chicago", "none"):
        raise ValueError("Unknown citation style")
    chicago = Chicago(citation_overrides) if citation_style == "chicago" else None
    esc = html.escape
    entries = sorted(entries, key=lambda e: e["title"].casefold())
    toc, articles = [], []
    for e in entries:
        ident = esc(e["id"], quote=True)
        toc.append('<li><a href="#%s">%s</a></li>' % (ident, esc(e["title"])))
        paragraphs = []
        for p in e["paragraphs"]:
            cites = " ".join('<a href="#%s-source-%d" aria-label="Source %d">[%d]</a>' % (ident, i, i, i) for i in p["source_ids"])
            text = without_citations(p["text"]) if citation_style == "links" else p["text"]
            paragraphs.append('<p>%s <sup>%s</sup></p>' % (esc(text), cites))
        sources = "".join('<li id="%s-source-%d"><a href="%s" rel="noopener noreferrer">%s</a></li>' %
                          (ident, s["id"], esc(s["url"], quote=True), esc(s["title"]))
                          for s in e["sources"] if safe_url(s["url"]))
        if citation_style == "none":
            paragraphs = ["<p>" + esc(without_citations(p["text"])) + "</p>" for p in e["paragraphs"]]
        if chicago:
            paragraphs = [chicago.paragraphs(e)]
            sources = ''
        if citation_style == "none":
            articles.append('<article id="%s"><p class="eyebrow">%s · %d words</p><h2>%s</h2>%s</article>' %
                            (ident, esc(e["category"]), word_count(e), esc(e["title"]), "".join(paragraphs)))
            continue
        articles.append('<article id="%s"><p class="eyebrow">%s · %d words</p><h2>%s</h2>%s%s<p class="meta">Generated %s · %s</p><a href="#contents">Back to contents ↑</a></article>' %
                        (ident, esc(e["category"]), word_count(e), esc(e["title"]), "".join(paragraphs), "" if citation_style != "links" else "<h3>Sources</h3><ol>" + sources + "</ol>", esc(e["generated_at"][:10]), "AI fact-check skipped (standard mode)" if e.get("generation_mode") == "standard" else "Automated evidence review passed"))
    if chicago:
        articles.append(chicago.render())
        if citation_report is not None:
            citation_report.extend(chicago.report())
        toc.append('<li><a href="#notes">Notes</a></li><li><a href="#bibliography">Bibliography</a></li>')
    intro = "" if not introduction else '<section id="preface"><h2>Preface</h2>%s</section>' % "".join('<p>%s</p>' % preface_paragraph(without_citations(p) if citation_style == "none" else p) for p in introduction["paragraphs"])
    if chicago and chicago.incomplete:
        intro += '<p class="meta">Chicago reference draft: formatted from saved source records. Missing authors, publication details, and source types need editorial verification; no missing metadata has been invented.</p>'
    citation_notice = "" if citation_style == "none" else " Citations support review but do not guarantee accuracy."
    output = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Encyclopedia of %s</title><style>
:root{color-scheme:light;--ink:#20382f;--paper:#ffffff}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:18px/1.75 Georgia,serif}main{max-width:960px;margin:auto;padding:50px 30px}header{border-bottom:3px solid var(--ink);padding:40px 0}h1{font-size:clamp(36px,6vw,64px);line-height:1.12;font-weight:normal}h2{font-size:34px;line-height:1.25}h3{font-size:22px}a{color:#256348;text-underline-offset:3px}article,section,nav{padding:35px 0;border-bottom:1px solid #cbd2c6}article,section{scroll-margin-top:24px}.eyebrow,.meta,small{font:13px/1.6 system-ui,sans-serif;letter-spacing:.04em}small{display:block;color:#667267}nav ol{columns:2;column-gap:35px;padding-left:24px}nav li{break-inside:avoid;margin:0 0 12px}sup{font:12px system-ui}footer{padding:35px 0;font:14px/1.6 system-ui}article p{text-align:left}.bibliography-entry{padding-left:2em;text-indent:-2em;overflow-wrap:anywhere}#notes li{margin-bottom:.8em;overflow-wrap:anywhere}#notes,#bibliography{break-before:page}@page{margin:20mm}@media(max-width:600px){nav ol{columns:1}main{padding:20px}}@media print{body{background:white;font-size:11pt}main{max-width:none;padding:0}article{break-before:page}a{color:inherit}nav ol{columns:2}.backlink{display:none}}
</style></head><body><main><header><p class="eyebrow">SAGE / SYNTHETIC AUTOMATED GENERATOR OF ENCYCLOPEDIAS</p><h1>Encyclopedia of %s</h1><p>%d entries · Written for the educated layperson%s</p></header>%s<nav id="contents" aria-label="Table of contents"><h2>Contents</h2>%s<ol>%s</ol></nav>%s<footer>Created with SAGE. AI-generated text; review status is shown on each article; human editorial review is required before publication.%s</footer></main></body></html>''' % (esc(config["subject"]), esc(config["subject"]), len(entries), " · PARTIAL DRAFT" if partial else "", intro, '<a href="#preface">Preface</a>' if introduction else "", "".join(toc), "".join(articles), citation_notice)
    if citation_style in ("none", "links"):
        status = '<p>%d entries · Written for the educated layperson%s</p>' % (len(entries), " · PARTIAL DRAFT" if partial else "")
        output = output.replace(status, "", 1)
        footer = '<footer>Created with SAGE. AI-generated text; review status is shown on each article; human editorial review is required before publication.' + citation_notice + '</footer>'
        output = output.replace(footer, "", 1)
    if edition == "kindle" or citation_style == "none":
        output = output.replace("columns:2", "columns:1")
    if citation_style == "none":
        output = output.replace("</style>", "nav ol{padding-left:0;margin-left:0;list-style-position:inside}nav li{padding-left:0;text-indent:0}.toc-theme{font-size:.9em}</style>", 1)
    if citation_style == "links":
        for entry in entries:
            review_status = "AI fact-check skipped (standard mode)" if entry.get("generation_mode") == "standard" else "Automated evidence review passed"
            metadata = '<p class="meta">Generated %s · %s</p>' % (esc(entry["generated_at"][:10]), review_status)
            output = output.replace(metadata, "")
    if edition == "kindle":
        output = output.replace("</style>", "main{max-width:none;padding:1em}h1{font-size:2em}h2{font-size:1.5em}article{page-break-before:always}</style>", 1)
    return output
