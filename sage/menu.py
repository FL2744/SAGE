"""Interactive terminal interface for the existing SAGE workflow."""
from pathlib import Path
import re

from .storage import read
from .models import MODEL_OPTIONS, default_model, validate_model


def ask(label, default=None):
    suffix = " [%s]" % default if default is not None else ""
    return input(label + suffix + ": ").strip() or default or ""


def ask_guidance():
    print("Enter short guidance directly, or @ followed by a UTF-8 text file path for long guidance.")
    print("Example: @AI-guidance.txt (paths may contain spaces). Blank means no guidance.")
    while True:
        value = ask("Editorial guidance")
        if not value.startswith("@"):
            return value
        path_text = value[1:].strip().strip('"').strip("'")
        if not path_text:
            print("Enter a filename after @.")
            continue
        try:
            text = Path(path_text).expanduser().read_text(encoding="utf-8-sig").strip()
        except (OSError, UnicodeError) as error:
            print("Cannot read guidance file: %s. Try again; your setup is retained." % error)
            continue
        print("Loaded %d characters of editorial guidance." % len(text))
        return text


def number(label, default=None):
    while True:
        value = ask(label, default)
        if not value and default is None:
            return None
        try:
            if int(value) > 0:
                return int(value)
        except ValueError:
            pass
        print("Enter a positive whole number.")


def yes(label, default="n"):
    while True:
        value = ask(label + " (y/n)", default).lower()
        if value in ("y", "yes", "n", "no"):
            return value in ("y", "yes")
        print("Enter y or n.")


def choose_model(current=None):
    current = current or default_model()
    print("\nInference model (Enter keeps %s):" % current)
    for index, (ident, label) in enumerate(MODEL_OPTIONS, 1):
        print("%d. %s (%s)" % (index, label, ident))
    print("5. Custom OpenAI model ID")
    while True:
        value = ask("Choose a number or enter a model ID", current)
        if value == "5":
            value = ask("Custom model ID")
        elif value.isdigit():
            index = int(value)
            if 1 <= index <= len(MODEL_OPTIONS):
                return MODEL_OPTIONS[index - 1][0]
            print("Choose a number from 1 to 5.")
            continue
        try:
            return validate_model(value)
        except ValueError as error:
            print(str(error))


def menu():
    from .cli import parser, run
    project = None
    print("\nSAGE — Synthetic Automated Generator of Encyclopedias")
    print("API generation uses your OPENAI_API_KEY and incurs API charges.")
    while True:
        try:
            print("\nCurrent project: " + (str(project) if project else "none"))
            if project:
                print("Inference model: " + read(project / "config.json")["model"])
            if project:
                print("Generation: standard (AI fact-check skipped)")
            print("1. Create a new project\n2. Open an existing project\n"
                  "3. Generate entry ideas\n4. List entries and progress\n"
                  "5. Generate articles\n6. Generate preface\n"
                  "7. Export HTML or Word (.docx)\n8. Build / resume encyclopedia\n9. Change inference model\n10. Add articles to this encyclopedia\n0. Exit")
            choice = ask("Choose an option")
            if choice == "0":
                print("Goodbye.")
                return
            if choice not in {str(i) for i in range(1, 11)}:
                print("Choose a number from 0 to 10.")
                continue
            if choice == "1":
                subject = ask("Encyclopedia subject")
                if not subject:
                    print("A subject is required.")
                    continue
                location = ask("Project folder", "projects/encyclopedia")
                count = number("Number of entries", 300)
                minimum = number("Minimum words per article", 500)
                maximum = number("Maximum words per article", 800)
                model = choose_model()
                guidance = ask_guidance()
                print("Optional website restriction: enter domains such as arxiv.org or mit.edu.")
                print("Put subject areas and chapter themes in editorial guidance. Blank searches all websites.")
                while True:
                    domains = ask("Allowed website domains (blank for unrestricted)")
                    values = domains.split()
                    if len(values) <= 100 and all(re.fullmatch(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}", d) for d in values):
                        break
                    print("This field accepts website domains, not topic categories or full URLs.")
                    if yes("Add that text to editorial guidance instead"):
                        guidance = (guidance + "\nAdditional coverage guidance: " + domains).strip()
                        domains = ""
                        print("Added to guidance. Website research will be unrestricted.")
                        break
                    print("Your setup is retained. Correct the domains or press Enter for unrestricted research.")
                args = parser().parse_args(["init", location, "--subject", subject,
                    "--count", str(count), "--min-words", str(minimum),
                    "--max-words", str(maximum), "--model", model,
                    "--guidance=" + guidance, "--domains", *domains.split()])
                run(args)
                project = Path(location).expanduser().resolve()
                continue
            if choice == "2":
                location = ask("Existing project folder (blank to cancel)")
                if location:
                    candidate = Path(location).expanduser().resolve()
                    if not (candidate / "config.json").exists():
                        print("No saved SAGE project in this folder. Choose option 1 to create it; an empty folder can be reused.")
                        continue
                    config = read(candidate / "config.json")
                    print("Opened: " + config["subject"])
                    project = candidate
                continue
            if project is None:
                print("Create or open a project first.")
                continue
            if choice == "10":
                print("Add article topics; generation happens when you choose Generate or Build.")
                while True:
                    title = ask("New article title (blank to finish)")
                    if not title:
                        break
                    category = ask("Category", "Country Overviews")
                    scope = ask("What should the article cover?",
                                "An overview of " + title + ".")
                    try:
                        run(parser().parse_args(["add", str(project), "--title=" + title,
                                                 "--category=" + category, "--scope=" + scope]))
                    except ValueError as error:
                        print("SAGE: " + str(error))
                        continue
                    if not yes("Add another article"):
                        break
                print("Choose 8 to build/resume, update the preface, and export the expanded book. "
                      "Completed articles are retained. Option 5 generates articles only.")
                continue
            if choice == "9":
                current = read(project / "config.json")["model"]
                model = choose_model(current)
                run(parser().parse_args(["model", str(project), "--model=" + model]))
                print("Saved. Future generation uses this model; completed articles are retained.")
                continue
            command = {"3": "ideas", "4": "list", "5": "generate",
                       "6": "preface", "7": "export", "8": "build"}[choice]
            argv = [command, str(project)]
            if command == "generate":
                entry = ask("Entry ID (blank for pending entries)")
                if entry:
                    argv += ["--entry", entry]
                else:
                    limit = number("Maximum articles this run (blank for all pending)")
                    if limit:
                        argv += ["--limit", str(limit)]
            if command == "build":
                limit = number("Maximum articles this run (blank for all pending)")
                if limit:
                    argv += ["--limit", str(limit)]
            filename = "encyclopedia.html"
            if command == "export":
                print("1. Web version\n2. Kindle version\n3. No references version\n4. Chicago references version\n5. Word document (.docx)")
                style = ask("Export version", "1")
                word_output = style == "5"
                if word_output:
                    argv += ["--format", "docx"]
                    print("1. Linked citations\n2. No references\n3. Chicago references")
                    reference = ask("Word reference style", "1")
                    if reference not in ("1", "2", "3"):
                        print("Choose 1, 2, or 3.")
                        continue
                    style = {"1": "1", "2": "3", "3": "4"}[reference]
                if style not in ("1", "2", "3", "4"):
                    print("Choose 1, 2, 3, 4, or 5.")
                    continue
                argv += ["--edition", {"1": "web", "2": "kindle", "3": "no-references", "4": "chicago"}[style]]
                if style == "2":
                    filename = "encyclopedia-kindle.html"
                if style == "3":
                    argv += ["--citations", "none"]
                    filename = "encyclopedia-no-references.html"
                if style == "4":
                    argv += ["--citations", "chicago"]
                    filename = "encyclopedia-chicago.html"
                    print("Missing authors trigger API web research (API charges apply). Results are cached.")
                    if yes("Research missing reference metadata now"):
                        limit = number("Maximum new reference lookups (blank for all)")
                        if limit:
                            argv += ["--citation-limit", str(limit)]
                    else:
                        argv.append("--offline-citations")
                if word_output:
                    filename = str(Path(filename).with_suffix(".docx"))
            if command in ("export", "build"):
                label = "Word output file" if filename.endswith(".docx") else "HTML output file"
                output = ask(label, str(project / filename))
                argv += ["--output", output]
            if command == "export":
                argv.append("--partial" if yes("Export a partial draft", default="y") else "--complete")
            run(parser().parse_args(argv))
            print("Done.")
        except EOFError:
            print("\nGoodbye.")
            return
        except KeyboardInterrupt:
            print("\nStopped. Saved progress is retained. Returning to menu.")
        except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
            print("SAGE: " + str(error))
