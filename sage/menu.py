"""Interactive terminal interface for the existing SAGE workflow."""
from pathlib import Path

from .storage import read
from .models import MODEL_OPTIONS, default_model, validate_model


def ask(label, default=None):
    suffix = " [%s]" % default if default is not None else ""
    return input(label + suffix + ": ").strip() or default or ""


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
                print("Generation mode: " + read(project / "config.json").get("generation_mode", "strict"))
            print("1. Create a new project\n2. Open an existing project\n"
                  "3. Generate entry ideas\n4. List entries and progress\n"
                  "5. Generate articles\n6. Generate preface\n"
                  "7. Export HTML\n8. Build / resume encyclopedia\n9. Change inference model\n10. Add articles to this encyclopedia\n11. Change generation mode\n0. Exit")
            choice = ask("Choose an option")
            if choice == "0":
                print("Goodbye.")
                return
            if choice not in {str(i) for i in range(1, 12)}:
                print("Choose a number from 0 to 11.")
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
                guidance = ask("Editorial guidance (optional)")
                domains = ask("Research domains, space-separated (blank for unrestricted)")
                args = parser().parse_args(["init", location, "--subject", subject,
                    "--count", str(count), "--min-words", str(minimum),
                    "--max-words", str(maximum), "--model", model,
                    "--guidance", guidance, "--domains", *domains.split()])
                run(args)
                project = Path(location).expanduser().resolve()
                continue
            if choice == "2":
                location = ask("Existing project folder (blank to cancel)")
                if location:
                    candidate = Path(location).expanduser().resolve()
                    config = read(candidate / "config.json")
                    print("Opened: " + config["subject"])
                    project = candidate
                continue
            if project is None:
                print("Create or open a project first.")
                continue
            if choice == "11":
                print("1. Standard: research + writing; flexible length, no AI fact-check")
                print("2. Strict: research + writing + AI fact-check and corrections")
                selected = ask("Generation mode", "1")
                if selected not in ("1", "2"):
                    print("Choose 1 or 2.")
                    continue
                run(parser().parse_args(["mode", str(project), "--mode",
                                        "standard" if selected == "1" else "strict"]))
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
                print("1. Web version\n2. Kindle version\n3. No references version\n4. Chicago references version")
                style = ask("Export version", "1")
                if style not in ("1", "2", "3", "4"):
                    print("Choose 1, 2, 3, or 4.")
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
            if command in ("export", "build"):
                output = ask("HTML output file", str(project / filename))
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
