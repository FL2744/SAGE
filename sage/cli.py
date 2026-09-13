import argparse
import json
from pathlib import Path
import re
import sys
from .api import API
from .models import default_model, validate_model
from . import ideas, entries, book
from .storage import read, save, lock


def positive(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("Must be positive")
    return result


def parser():
    p = argparse.ArgumentParser(description="SAGE — Synthetic Automated Generator of Encyclopedias")
    sub = p.add_subparsers(dest="command", required=False)
    sub.add_parser("menu", help="Open the interactive menu")
    init = sub.add_parser("init", help="Create a project without API calls")
    init.add_argument("project", type=Path)
    init.add_argument("--subject", required=True)
    init.add_argument("--count", type=positive, default=300)
    init.add_argument("--min-words", type=positive, default=500)
    init.add_argument("--max-words", type=positive, default=800)
    init.add_argument("--model", default=default_model())
    init.add_argument("--guidance", default="")
    init.add_argument("--domains", nargs="*", default=[], help="Optional authoritative search domain allowlist")
    for name in ("ideas", "list", "generate", "preface", "export", "build"):
        cmd = sub.add_parser(name)
        cmd.add_argument("project", type=Path)
        if name in ("generate", "build"):
            cmd.add_argument("--retry-skipped", action="store_true", help="Retry articles previously skipped after errors")
            cmd.add_argument("--limit", type=positive, help="Maximum pending entries to attempt this run")
        if name == "generate":
            cmd.add_argument("--entry", help="Generate one entry ID from the list")
        if name in ("export", "build"):
            cmd.add_argument("--output", type=Path)
            cmd.add_argument("--citation-limit", type=positive, help="Maximum new API reference lookups")
            cmd.add_argument("--offline-citations", action="store_true", help="Use saved references without API lookups")
            cmd.add_argument("--edition", choices=("web", "kindle", "no-references", "chicago"))
            cmd.add_argument("--citations", choices=("links", "chicago", "none"), default="links")
        if name == "export":
            completeness = cmd.add_mutually_exclusive_group()
            completeness.add_argument("--partial", dest="partial", action="store_true", help="Export saved articles as a partial draft (default)")
            completeness.add_argument("--complete", dest="partial", action="store_false", help="Require all articles and a current preface")
            cmd.set_defaults(partial=True)
    model = sub.add_parser("model", help="Show or change the saved project model")
    model.add_argument("project", type=Path)
    model.add_argument("--model", help="Model ID to save for future inference")
    add = sub.add_parser("add", help="Add a pending article without API calls")
    add.add_argument("project", type=Path)
    add.add_argument("--title", required=True)
    add.add_argument("--category", required=True)
    add.add_argument("--scope", required=True)
    mode = sub.add_parser("mode", help="Choose standard or strict generation")
    mode.add_argument("project", type=Path)
    mode.add_argument("--mode", choices=("standard", "strict"), required=True)
    return p


def load_ideas(project):
    path = project / "ideas.json"
    if not path.exists():
        raise ValueError("Run the ideas command first.")
    result = read(path)
    ids, titles = set(), set()
    for idea in result:
        ident, title = idea["id"], ideas.normalized(idea["title"])
        if not re.fullmatch(r"e[0-9]{4,}", ident) or ident in ids or not title or title in titles:
            raise ValueError("ideas.json has invalid or duplicate IDs/titles.")
        ids.add(ident)
        titles.add(title)
    return result


def accepted(project, config, planned):
    result = []
    for idea in planned:
        path = project / "entries" / (idea["id"] + ".json")
        if path.exists():
            article = read(path)
            if any(article[k] != idea[k] for k in ("id", "title", "category", "scope")):
                raise ValueError("Entry %s has changed in ideas.json; remove its saved entry to regenerate." % idea["id"])
            standard = article.get("generation_mode") == "standard" and article["review"].get("skipped") is True
            entries.validate(article, article["sources"], config, enforce_length=not standard)
            if article["review"]["issues"] or (not standard and not article["review"]["passed"]):
                raise ValueError("Saved entry has not passed automated review.")
            result.append(article)
    return result


def run(args):
    project = args.project.expanduser().resolve()
    with lock(project):
        ideas.recover_addition(project)
        if args.command == "init":
            if (project / "config.json").exists():
                raise ValueError("Project already exists.")
            if not args.subject.strip() or args.min_words > args.max_words:
                raise ValueError("Supply a subject and a valid word range.")
            if len(args.domains) > 100 or any(not re.fullmatch(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}", d) for d in args.domains):
                raise ValueError("Use at most 100 bare domain names (no URLs).")
            args.model = validate_model(args.model)
            save(project / "config.json", {k: getattr(args, k) for k in ("subject", "count", "min_words", "max_words", "model", "guidance", "domains")})
            print("Created " + str(project))
            return
        config = read(project / "config.json")
        if args.command == "mode":
            config["generation_mode"] = args.mode
            save(project / "config.json", config)
            print("Generation mode: " + args.mode)
            return
        if args.command == "add":
            planned = load_ideas(project) if (project / "ideas.json").exists() else []
            item, count = ideas.add(project, config, planned, args.title, args.category, args.scope)
            print("Added %s: %s (pending). Target: %d entries." % (item["id"], item["title"], count))
            return
        if args.command == "model":
            if args.model is not None:
                config["model"] = validate_model(args.model)
                save(project / "config.json", config)
            print("Model: " + config["model"])
            return
        def log(record):
            with (project / "usage.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        api = None
        def client():
            nonlocal api
            if api is None:
                api = API(config["model"], log)
            return api
        if args.command in ("ideas", "build"):
            ideas.generate(client(), project, config)
            if args.command == "ideas":
                return
        planned = load_ideas(project)
        done = accepted(project, config, planned)
        done_ids = {e["id"] for e in done}
        skipped_ids = {i["id"] for i in planned
                       if (project / "errors" / (i["id"] + ".json")).exists()
                       and read(project / "errors" / (i["id"] + ".json")).get("skipped", False)}
        if args.command == "list":
            for i in planned:
                print('%s [%s] %s — %s' % (i["id"], "ready" if i["id"] in done_ids else "skipped" if i["id"] in skipped_ids else "pending", i["title"], i["category"]))
            print('%d/%d entries accepted; target %d' % (len(done), len(planned), config["count"]))
            return
        if args.command in ("generate", "build"):
            selected = getattr(args, "entry", None)
            if selected and selected not in {i["id"] for i in planned}:
                raise ValueError("Unknown entry ID: " + selected)
            pending = [i for i in planned if i["id"] not in done_ids and (not selected or selected == i["id"])]
            if not selected and not args.retry_skipped:
                pending = [i for i in pending if i["id"] not in skipped_ids]
                if skipped_ids:
                    print("Leaving %d previously skipped articles for later. Use option 5 with an entry ID to retry one." % len(skipped_ids))
            pending = pending[:args.limit] if args.limit else pending
            failures = []
            for idea in pending:
                print("Generating %s: %s" % (idea["id"], idea["title"]), flush=True)
                try:
                    article = entries.generate(client(), project, config, idea)
                    save(project / "entries" / (idea["id"] + ".json"), article)
                    error_path = project / "errors" / (idea["id"] + ".json")
                    if error_path.exists():
                        error_path.unlink()
                except (ValueError, RuntimeError, OSError) as error:
                    save(project / "errors" / (idea["id"] + ".json"), dict(error=str(error), issues=getattr(error, "issues", []), skipped=True))
                    print("Skipped %s: %s. Continuing with the next article." % (idea["id"], error), file=sys.stderr)
                    failures.append(idea["id"])
            if failures:
                print("Skipped %d articles; details saved in errors/." % len(failures))
            if args.command == "generate":
                return
            done = accepted(project, config, planned)
        complete = len(done) == len(planned) == config["count"]
        if args.command == "build" and not complete:
            print("Build finished with %d/%d accepted entries; exporting a partial draft." % (len(done), config["count"]))
            if not done:
                print("No accepted articles to export yet. Review errors/ or retry a skipped entry with option 5.")
                return
        if args.command == "preface" or (args.command == "build" and complete):
            if not complete:
                raise ValueError("Generation progress saved. Finish all planned entries before creating the preface.")
            path = project / "preface.json"
            if not path.exists() or read(path).get("fingerprint") != book.fingerprint(done):
                save(path, book.preface(client(), config, done))
            if args.command == "preface":
                return
        if args.command in ("export", "build"):
            partial = getattr(args, "partial", False) or (args.command == "build" and not complete)
            if not done or (not complete and not partial):
                raise ValueError("Full export requires all entries. Use export --partial to preview accepted entries.")
            path = project / "preface.json"
            intro = read(path) if path.exists() else None
            if intro and intro.get("fingerprint") != book.fingerprint(done):
                intro = None
            if not partial and not intro:
                raise ValueError("Run preface first; it is missing or stale.")
            edition = getattr(args, "edition", None)
            filename = {"kindle": "encyclopedia-kindle.html", "no-references": "encyclopedia-no-references.html",
                        "chicago": "encyclopedia-chicago.html"}.get(edition, "encyclopedia.html")
            output = (args.output or project / filename).expanduser().resolve()
            if output.suffix.lower() != ".html":
                raise ValueError("Output filename must end in .html")
            output.parent.mkdir(parents=True, exist_ok=True)
            style = {"web": "links", "kindle": "links", "no-references": "none", "chicago": "chicago"}.get(edition, getattr(args, "citations", "links"))
            overrides_path = project / "citations.json"
            overrides = read(overrides_path) if style == "chicago" and overrides_path.exists() else {}
            if style == "chicago" and not getattr(args, "offline_citations", False):
                from .citation_research import enrich
                overrides = enrich(client, project, done, overrides, getattr(args, "citation_limit", None))
            elif style == "chicago":
                from .citation_research import enrich
                overrides = enrich(client, project, done, overrides, limit=0)
            citation_report = []
            rendered = book.render(config, done, intro, partial, citation_style=style,
                                   citation_overrides=overrides, citation_report=citation_report, edition=edition)
            output.write_text(rendered, encoding="utf-8")
            if style == "chicago":
                report_path = output.with_suffix(".citation-review.json")
                save(report_path, citation_report)
                print("Chicago notes and bibliography exported from saved metadata. "
                      "%d references need metadata review; see %s" % (len(citation_report), report_path))
            print("Exported " + str(output))


def main():
    args = parser().parse_args()
    try:
        if args.command in (None, "menu"):
            from .menu import menu
            menu()
        else:
            run(args)
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        print("SAGE: " + str(error), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopped. Saved progress is retained; rerun to resume.", file=sys.stderr)
        sys.exit(130)
