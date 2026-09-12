"""Research, composition and separate automated evidence review."""
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from .api import obj, STRING, STRINGS
from .storage import save

ARTICLE = obj(paragraphs={"type": "array", "items": obj(text=STRING, source_ids={"type": "array", "items": {"type": "integer"}})}, summary=STRING)
REVIEW = obj(passed={"type": "boolean"}, issues=STRINGS, suggestions=STRINGS,
             affected_paragraphs={"type": "array", "items": {"type": "integer", "minimum": 1}},
             summary_needs_revision={"type": "boolean"})


def preserve_unflagged(previous, candidate, review):
    """Only apply changes to passages identified by the factual review."""
    if len(candidate["paragraphs"]) != len(previous["paragraphs"]):
        raise ValueError("Keep the original paragraph count when revising flagged passages.")
    affected = review.get("affected_paragraphs", list(range(1, len(previous["paragraphs"]) + 1)))
    if any(type(i) is not int or i < 1 or i > len(previous["paragraphs"]) for i in affected):
        raise ValueError("Review referenced an invalid paragraph number.")
    return dict(paragraphs=[new if i in affected else old
                           for i, (old, new) in enumerate(zip(previous["paragraphs"], candidate["paragraphs"]), 1)],
                summary=candidate["summary"] if review.get("summary_needs_revision", True) else previous["summary"])



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
    if config.get("generation_mode", "strict") == "standard":
        return standard_draft(api, project, config, idea, base)
    feedback = []
    previous = None
    previous_review = None
    report = project / "reviews" / (idea["id"] + ".json")
    format_failures = 0
    review_attempts = 0
    for attempt in range(6):
        print("  Drafting (draft %d; fact-check round %d/3)..." % (attempt + 1, review_attempts + 1), flush=True)
        article, _ = api.call(
            "Write an original encyclopedia entry for an educated layperson at college-graduate reading level. "
            "Use clear explanatory prose, define jargon, distinguish consensus from dispute, date time-sensitive claims, "
            "and avoid unsupported generalizations. No HTML, Markdown or headings in paragraph text. "
            "Write %d–%d words in paragraph text, excluding citations and summary. "
            "Each paragraph must cite the supporting source IDs. Use only supplied evidence; do not invent facts. "
            "Use corrected evidence over superseded claims. Remove or qualify unsupported claims. "
            "For a revision, fix only blocking feedback. Keep paragraph count and order unchanged and copy "
            "unflagged paragraphs verbatim, including citations. Do not introduce new claims or optional context. "
            "Change the synopsis only when marked for revision. Prior draft claims are not evidence. "
            "Include an accurate 100–150-word synopsis of the complete entry for the eventual preface. "
            "Research data: %s. Corrections from previous attempt: %s. Previous draft: %s. Revision scope: %s" %
            (config["min_words"], config["max_words"], json.dumps(base), json.dumps(feedback, ensure_ascii=False), json.dumps(previous), json.dumps(previous_review)), ARTICLE)
        try:
            if previous is not None and previous_review is not None:
                article = preserve_unflagged(previous, article, previous_review)
            validate(article, sources, config)
        except ValueError as error:
            format_failures += 1
            feedback = (previous_review["issues"] if previous_review else []) + [str(error)]
            save(report, dict(attempt=attempt + 1, validation_issues=feedback, draft=article, sources=sources))
            print("  Validation: %s (format failure %d/3)." % (error, format_failures), flush=True)
            if format_failures >= 3:
                break
            if previous_review is None:
                previous = article
            continue
        prior_draft = previous
        previous = article
        review_attempts += 1
        print("  Fact-checking (round %d/3)..." % review_attempts, flush=True)
        review, review_citations = api.call(
            "Independently fact-check this encyclopedia entry using web search and the cited sources. "
            "Check all material factual claims, dates, names, paragraph citation support, source authority and independence, "
            "balanced framing, and whether the synopsis faithfully covers the article. "
            "Separate blocking factual issues from non-blocking editorial suggestions. issues must contain ONLY "
            "material factual errors, unsupported central claims, invalid or inadequate citations for material claims, "
            "or materially misleading framing or synopsis. Describe the exact claim, paragraph number, evidence gap, "
            "and minimal correction for each blocker. Put wording preferences, optional context, stylistic improvements, "
            "and minor qualifications that do not change factual meaning in suggestions; these must not cause failure. "
            "Set passed=true exactly when issues is empty. affected_paragraphs must list the 1-based paragraph numbers "
            "requiring blocking corrections, never paragraphs with suggestions alone. Set summary_needs_revision only "
            "when a factual correction also requires updating the synopsis or the synopsis is materially misleading. "
            "On subsequent reviews, verify previous blockers and changed passages first; do not reopen cleared text "
            "for editorial preferences. Still report newly discovered material factual errors with specific evidence. Data: " +
            json.dumps(dict(base=base, article=article, previous_draft=prior_draft, previous_review=previous_review)), REVIEW, search=True, domains=config["domains"])
        # Suggestions are advisory; the explicit blocking list controls acceptance.
        review["passed"] = not bool(review["issues"])
        review.setdefault("suggestions", [])
        previous_review = review
        save(report, dict(attempt=attempt + 1, review=review, citations=review_citations, draft=article, sources=sources))
        if review["passed"] and not review["issues"]:
            print("  Accepted (%d editorial suggestions saved in review)." % len(review["suggestions"]), flush=True)
            return dict(**idea, **article, sources=sources, review=review,
                        generated_at=datetime.now(timezone.utc).isoformat(), model=api.model)
        feedback = review["issues"] or ["Evidence review did not pass."]
        if review_attempts >= 3:
            break
        if review_attempts < 3:
            print("  Review found %d blocking issues; researching corrections..." % len(feedback), flush=True)
            corrected, new_citations = api.call(
                "Repair the evidence for this encyclopedia entry using targeted web research. "
                "Investigate every reviewer issue against authoritative, accessible sources. "
                "Read replacement or additional sources, not just snippets or publisher blurbs. "
                "Check publication dates against the supplied date; distinguish forthcoming work. "
                "Return a complete corrected evidence brief with inline citations, retaining supported evidence "
                "and identifying superseded claims, unsupported claims to remove, and unresolved uncertainty. "
                "Reviewer findings are leads to verify, not established facts. Do not invent support to secure approval. Data: " +
                json.dumps(dict(base=base, draft=article, issues=feedback), ensure_ascii=False),
                search=True, domains=config["domains"])
            merge_sources(sources, new_citations)
            base["research"] = corrected
            base.setdefault("corrections", []).append(dict(attempt=attempt + 1, issues=list(feedback),
                                                          research=corrected, citations=new_citations))
            save(project / "research" / (idea["id"] + ".json"), base)
    raise EntryFailure(feedback, report)
