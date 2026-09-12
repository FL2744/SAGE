"""Preface synthesis and safe, self-contained HTML export."""
import hashlib
import html
import json
from .api import obj, STRINGS
from .entries import safe_url, word_count


def fingerprint(entries):
    return hashlib.sha256(json.dumps(entries, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def preface(api, config, entries):
    # Summaries come from the full accepted articles, not merely the topic list.
    summaries = [dict(title=e["title"], category=e["category"], summary=e["summary"]) for e in entries]
    result, _ = api.call(
        "Write a 600–900-word preface to an encyclopedia for educated laypeople. Synthesize the entire supplied "
        "set of entry synopses: explain scope, major themes, connections and limits. Do not introduce new factual "
        "claims or claim exhaustive coverage. Use plain paragraphs without markup. Subject: " + config["subject"] +
        ". All accepted entry synopses: " + json.dumps(summaries), obj(paragraphs=STRINGS))
    if not result["paragraphs"] or not all(p.strip() for p in result["paragraphs"]):
        raise ValueError("Empty preface returned.")
    return dict(**result, fingerprint=fingerprint(entries))


def render(config, entries, introduction=None, partial=False):
    esc = html.escape
    entries = sorted(entries, key=lambda e: e["title"].casefold())
    toc, articles = [], []
    for e in entries:
        ident = esc(e["id"], quote=True)
        toc.append('<li><a href="#%s">%s</a><small>%s</small></li>' % (ident, esc(e["title"]), esc(e["category"])))
        paragraphs = []
        for p in e["paragraphs"]:
            cites = " ".join('<a href="#%s-source-%d" aria-label="Source %d">[%d]</a>' % (ident, i, i, i) for i in p["source_ids"])
            paragraphs.append('<p>%s <sup>%s</sup></p>' % (esc(p["text"]), cites))
        sources = "".join('<li id="%s-source-%d"><a href="%s" rel="noopener noreferrer">%s</a></li>' %
                          (ident, s["id"], esc(s["url"], quote=True), esc(s["title"]))
                          for s in e["sources"] if safe_url(s["url"]))
        articles.append('<article id="%s"><p class="eyebrow">%s · %d words</p><h2>%s</h2>%s<h3>Sources</h3><ol>%s</ol><p class="meta">Generated %s · %s</p><a href="#contents">Back to contents ↑</a></article>' %
                        (ident, esc(e["category"]), word_count(e), esc(e["title"]), "".join(paragraphs), sources, esc(e["generated_at"][:10]), "AI fact-check skipped (standard mode)" if e.get("generation_mode") == "standard" else "Automated evidence review passed"))
    intro = "" if not introduction else '<section id="preface"><h2>Preface</h2>%s</section>' % "".join('<p>%s</p>' % esc(p) for p in introduction["paragraphs"])
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Encyclopedia of %s</title><style>
:root{color-scheme:light;--ink:#20382f;--paper:#faf8f1}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:18px/1.75 Georgia,serif}main{max-width:960px;margin:auto;padding:50px 30px}header{border-bottom:3px solid var(--ink);padding:40px 0}h1{font-size:clamp(36px,6vw,64px);line-height:1.12;font-weight:normal}h2{font-size:34px;line-height:1.25}h3{font-size:22px}a{color:#256348;text-underline-offset:3px}article,section,nav{padding:35px 0;border-bottom:1px solid #cbd2c6}article,section{scroll-margin-top:24px}.eyebrow,.meta,small{font:13px/1.6 system-ui,sans-serif;letter-spacing:.04em}small{display:block;color:#667267}nav ol{columns:2;column-gap:35px;padding-left:24px}nav li{break-inside:avoid;margin:0 0 12px}sup{font:12px system-ui}footer{padding:35px 0;font:14px/1.6 system-ui}article p{text-align:left}@media(max-width:600px){nav ol{columns:1}main{padding:20px}}@media print{body{background:white;font-size:11pt}main{max-width:none;padding:0}article{break-before:page}a{color:inherit}nav ol{columns:2}}
</style></head><body><main><header><p class="eyebrow">SAGE / SYNTHETIC AUTOMATED GENERATOR OF ENCYCLOPEDIAS</p><h1>Encyclopedia of %s</h1><p>%d entries · Written for the educated layperson%s</p></header>%s<nav id="contents" aria-label="Table of contents"><h2>Contents</h2>%s<ol>%s</ol></nav>%s<footer>Created with SAGE. AI-generated text; review status is shown on each article; human editorial review is required before publication. Citations support review but do not guarantee accuracy.</footer></main></body></html>''' % (esc(config["subject"]), esc(config["subject"]), len(entries), " · PARTIAL DRAFT" if partial else "", intro, '<a href="#preface">Preface</a>' if introduction else "", "".join(toc), "".join(articles))
