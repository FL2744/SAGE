"""Research and composition with basic citation validation."""
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from .api import obj, STRING
from .storage import save

ARTICLE = obj(paragraphs={"type": "array", "items": obj(text=STRING, source_ids={"type": "array", "items": {"type": "integer"}})}, summary=STRING)
def word_count(article):
    return len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", " ".join(p["text"] for p in article["paragraphs"])))


def safe_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.hostname) and not parsed.username


def validate(article, sources, config, enforce_length=True):
    count = word_count(article)
    if enforce_length and not config["min_words"] <= count <= config["max_words"]:
        raise ValueError("Article has %d words; expected %d–%d." % (count, config["min_words"], config["max_words"]))
    valid = {s["id"] for s in sources}
    used = set()
    for paragraph in article["paragraphs"]:
        ids = paragraph["source_ids"]
        if not paragraph["text"].strip() or not ids or any(type(i) is not int or i not in valid for i in ids):
            raise ValueError("Every paragraph must cite known source IDs.")
        used.update(ids)
    if len(used) < 2:
        raise ValueError("Entry must cite at least two sources.")
    if not article["summary"].strip():
        raise ValueError("Entry summary is missing.")


class EntryFailure(ValueError):
    def __init__(self, issues, report):
        self.issues = issues
        super().__init__("Entry reached its retry limit (%d unresolved issues). Full report: %s"
                         % (len(issues), report))


def merge_sources(sources, citations):
    seen = {s["url"] for s in sources}
    for cite in citations:
        url = cite["url"]
        if safe_url(url) and url not in seen:
            seen.add(url)
            sources.append(dict(id=len(sources) + 1, url=url, title=cite.get("title") or url))


def standard_draft(api, project, config, idea, base):
    feedback = []
    report = project / "reviews" / (idea["id"] + ".json")
    for attempt in range(2):
        print("  Writing standard draft (%d/2; no separate fact-check)..." % (attempt + 1), flush=True)
        article, _ = api.call(
            "Write a clear encyclopedia article for an educated general reader using the supplied research. "
            "Aim for %d–%d words, but treat length as guidance. Avoid unsupported claims. "
            "Every paragraph must cite supplied source IDs; cite at least two distinct sources overall. "
            "Include a brief faithful synopsis in summary. Use plain paragraphs without headings or markup. "
            "Correct any listed structural problems. Research: %s. Corrections: %s" %
            (config["min_words"], config["max_words"], json.dumps(base), json.dumps(feedback)), ARTICLE)
        try:
            validate(article, base["sources"], config, enforce_length=False)
        except ValueError as error:
            feedback = [str(error)]
            save(report, dict(validation_issues=feedback, draft=article, sources=base["sources"]))
            print("  Citation/structure check: " + str(error), flush=True)
            continue
        review = dict(passed=False, skipped=True, issues=[], suggestions=[], mode="standard")
        save(report, dict(review=review, draft=article, sources=base["sources"]))
        print("  Saved (%d words; citation structure checked, AI fact-check skipped)." % word_count(article), flush=True)
        return dict(**idea, **article, sources=base["sources"], review=review, generation_mode="standard",
                    generated_at=datetime.now(timezone.utc).isoformat(), model=api.model)
    raise EntryFailure(feedback, report)


def generate(api, project, config, idea):
    context = json.dumps(dict(subject=config["subject"], guidance=config["guidance"], entry=idea, date=datetime.now(timezone.utc).date().isoformat()), ensure_ascii=False)
    print("  Researching sources...", flush=True)
    research, citations = api.call(
        "Research this encyclopedia entry: " + context +
        ". Search and read authoritative sources: scholarly publications, university presses, museums, scientific bodies, "
        "official statistics, and relevant community-led institutions. Compare at least two independent sources. "
        "Give a detailed evidence brief with inline citations supporting definitions, history, dates, major claims, "
        "disputed interpretations and current facts. Explain source authority and uncertainty. Never use search snippets alone as proof.",
        search=True, domains=config["domains"])
    sources = []
    merge_sources(sources, citations)
    if len(sources) < 2:
        raise ValueError("Research did not return at least two usable cited sources.")
    base = dict(context=context, research=research, sources=sources)
    save(project / "research" / (idea["id"] + ".json"), base)
    return standard_draft(api, project, config, idea, base)
