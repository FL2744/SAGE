"""Generate a resumable, categorized editorial list in manageable batches."""
import json
import re
import unicodedata
from .api import obj, STRING
from .storage import save, read

SCHEMA = obj(ideas={"type": "array", "items": obj(title=STRING, category=STRING, scope=STRING)})


def normalized(title):
    return " ".join(unicodedata.normalize("NFKC", title).casefold().split())


def next_id(project, planned):
    identifiers = [item["id"] for item in planned]
    for folder in ("entries", "research", "reviews", "errors"):
        identifiers.extend(path.stem for path in (project / folder).glob("*.json"))
    numbers = [int(ident[1:]) for ident in identifiers if re.fullmatch(r"e[0-9]{4,}", ident)]
    return "e%04d" % (max(numbers, default=0) + 1)


def recover_addition(project):
    """Finish an interrupted two-file update while holding the project lock."""
    journal = project / ".pending-addition.json"
    if journal.exists():
        pending = read(journal)
        save(project / "ideas.json", pending["ideas"])
        save(project / "config.json", pending["config"])
        journal.unlink()


def add(project, config, planned, title, category, scope):
    fields = dict(title=title.strip(), category=category.strip(), scope=scope.strip())
    if not all(fields.values()):
        raise ValueError("Title, category, and scope are required.")
    if normalized(fields["title"]) in {normalized(item["title"]) for item in planned}:
        raise ValueError("An entry with this title already exists. Choose a distinct topic or title.")
    item = dict(id=next_id(project, planned), **fields)
    updated = dict(config, count=max(config["count"], len(planned)) + 1)
    # Persist the intended update before either file changes, allowing safe recovery.
    save(project / ".pending-addition.json", dict(ideas=planned + [item], config=updated))
    recover_addition(project)
    return item, updated["count"]


def generate(api, project, config):
    path = project / "ideas.json"
    ideas = read(path) if path.exists() else []
    seen = {normalized(i["title"]) for i in ideas}
    stalls = 0
    while len(ideas) < config["count"]:
        count = min(25, config["count"] - len(ideas))
        data, _ = api.call(
            "Plan an encyclopedia for college-educated laypeople. Generate exactly %d distinct entry ideas. "
            "Aim for balanced coverage of foundational concepts, history, people, places, applications and debates as appropriate. "
            "Avoid overlapping subjects, stereotypes and treating diverse peoples as homogeneous. "
            "Account for existing coverage and fill gaps. Each scope should describe a feasible 500–800-word article. "
            "Subject and editorial guidance: %s. Already planned: %s" %
            (count, json.dumps(config), json.dumps(ideas)), SCHEMA)
        added = 0
        for item in data["ideas"]:
            key = normalized(item["title"])
            if not key or key in seen or len(ideas) >= config["count"]:
                continue
            if not item["category"].strip() or not item["scope"].strip():
                continue
            seen.add(key)
            ideas.append(dict(id=next_id(project, ideas), **item))
            added += 1
        save(path, ideas)
        print("Ideas: %d/%d" % (len(ideas), config["count"]), flush=True)
        stalls = stalls + 1 if not added else 0
        if stalls >= 3:
            raise ValueError("No new distinct ideas after three batches. Review ideas.json and retry.")
    return ideas
