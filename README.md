![SAGE logo](SAGE-logo.png)

# SAGE
**Synthetic Automated Generator of Encyclopedias**

A Python 3.9+ command-line application that turns any subject into a researched encyclopedia with categorized entry ideas, 500–800-word articles, a synthesized preface, linked citations, and a hotlinked table of contents in one self-contained HTML file. Works on macOS/Linux; no third-party dependencies are required.

## Interactive menu

Start SAGE from its project folder:

```sh
cd ~/VIBES/SAGE
python3 -m sage
```

Choose a numbered option to create or open a project, generate ideas, list progress,
generate articles, create the preface, export HTML, or build/resume the whole book.
Prompts show defaults in brackets; press Enter to accept them. Create a project
first, then generate ideas before articles. You can limit article generation to a
small batch or a single entry ID. Export a partial draft to preview saved articles.
Use option 0 to exit. Ctrl-C stops the current operation and returns to the menu;
completed work is retained. Errors also return to the menu so you can correct them.

Set `OPENAI_API_KEY` in your terminal before starting generation. Creating projects,
listing entries, and exporting saved content do not require API access.
`python3 -m sage menu` (or `sage` after installation) also opens the menu.
The commands below remain available for scripting.

## Add articles to an existing encyclopedia

Open the project with option **2**, then choose **10. Add articles to this encyclopedia**.
Enter a title, category, and description of what the article should cover. For example,
use `Qatar` with category `Country Overviews` and scope `Geography, history, people,
culture, government, and economy`. You can add several articles in one visit.

SAGE assigns unique entry IDs, rejects duplicate titles, and increases the target
count by one per addition (preserving any unfilled slots in an unfinished idea plan).
Adding topics does not call the API or change completed articles. An interrupted
save is recovered on the next project command.

Choose **8. Build / resume encyclopedia** afterward to generate pending articles,
refresh the preface, and export the expanded HTML book. Existing accepted articles
are skipped. Option **5** can generate a single new entry or a limited batch first.
Previously exported HTML stays as it was until you export/build again.

The equivalent command is:

```sh
python3 -m sage add projects/arab-world --title Qatar --category 'Country Overviews' --scope 'Geography, history, people, culture, government, and economy.'
```

## Inference models

New projects default to **GPT-5.6 Luna** (`gpt-5.6-luna`). The model picker offers
Luna, Terra, Sol, Astra, or a custom OpenAI model ID. Press Enter to accept the
shown default. `OPENAI_MODEL` overrides the default for new projects.

Open a project and choose **9. Change inference model** to save a different model.
The active model is displayed above the main menu and applies to idea generation,
research, drafting, review, and preface generation. Existing projects keep their
saved model until changed; completed content is retained when switching models.

For scripting:

```sh
python3 -m sage model projects/arab-world
python3 -m sage model projects/arab-world --model gpt-5.6-luna
```

Custom IDs use the OpenAI Responses API and must support structured outputs and
web search. Model access depends on your API account. See the
[OpenAI model catalog](https://developers.openai.com/api/docs/models).

## Quick start

```sh
cd ~/SAGE
export OPENAI_API_KEY='your-key-here'
python3 -m sage init projects/arab-world --subject 'The Arab world' --count 300
python3 -m sage ideas projects/arab-world
python3 -m sage list projects/arab-world
python3 -m sage generate projects/arab-world --entry e0001
python3 -m sage export projects/arab-world --partial
open projects/arab-world/encyclopedia.html
```

Review or edit `projects/arab-world/ideas.json` before bulk generation. Keep IDs unique and unchanged; edit titles, categories, and scopes. If you change the desired number of entries, update `count` in `config.json`. Already generated entries whose ideas changed must be removed from `entries/` before regeneration. Exact normalized duplicate titles are rejected; conceptual overlap still needs editorial review.

Finish the project:

```sh
python3 -m sage build projects/arab-world
open projects/arab-world/encyclopedia.html
```

`build` completes ideas, generates pending entries, synthesizes the preface, and exports. Existing accepted entries are skipped. To work in small batches, use `generate --limit 5`. A limited `build` saves progress but reports that the book remains incomplete. Individual steps are also available:

```sh
python3 -m sage generate projects/arab-world
python3 -m sage preface projects/arab-world
python3 -m sage export projects/arab-world --output ~/SAGE/arab-world.html
```

Use any subject, e.g. `--subject Chemistry` or `--subject 'Indigenous peoples of the Americas'`. Add `--guidance 'Emphasize community perspectives and contemporary life alongside history'`. Optional `--domains unesco.org si.edu` restricts research to those domains; choose an appropriate, sufficiently broad set for your subject. The model is configurable at initialization with `--model` or `OPENAI_MODEL`, and afterward in `config.json`. Default: `gpt-5.6-luna`; your account must support the model, Responses, structured outputs, and web search.

Optional installation: `python3 -m pip install -e .` exposes the `sage` command (a virtual environment is recommended).

## Research and editorial quality

All projects use standard generation: one web-research call and one writing call,
with at most one additional writing attempt for invalid citations or malformed
content. Article length is guidance. There is no separate AI fact-check or
review-revision loop. Sources are retained and basic citation IDs are validated.
Legacy `generation_mode` settings are ignored; saved articles remain usable.

SAGE cannot guarantee factual accuracy or source quality. Read the sources and
review generated prose before publication. The preface synthesizes accepted
article summaries. HTML escapes generated text and supports print.

## Persistence, costs, and operation

- Project files: `config.json`, `ideas.json`, `entries/`, `research/`, `reviews/`, `errors/`, `preface.json`, `usage.jsonl`, and `encyclopedia.html`.
- Saves are atomic. A project lock prevents two local commands from modifying the same project simultaneously.
- Ctrl-C retains completed work. Rerun the command to resume; an interrupted entry may need to repeat its API calls.
- API calls incur your OpenAI API charges. A 300-entry volume normally needs 12 idea batches, at least 600 entry calls, and one preface call, plus revision/retry calls and web-search charges. Start with one entry to assess quality and usage. There is no built-in dollar budget; use API account spending controls and `--limit`.
- Token usage and response IDs are logged without the API key. The key is read only from the environment. Requests use `store=false`; OpenAI's applicable data policies still apply.
- Rate limits and selected server errors use bounded exponential retries. Network errors stop the current entry; check `errors/` and rerun.
- Do not run multiple writers against the same project from different machines/network filesystems.

## Development

```sh
python3 -m unittest discover -s tests -v
```

Offline tests exercise the workflow with mocked API responses. Live generation requires your API key and is not part of the test suite.

API references: [Responses structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [web search and citations](https://developers.openai.com/api/docs/guides/tools-web-search).

## Bounded retries and unattended builds

Each article gets at most two writing attempts. After an error, SAGE saves the
report, skips the entry, and continues. Later builds leave skipped entries for
later; option 5 with an entry ID retries one. CLI `--retry-skipped` retries them
in bulk. Incomplete builds export the saved articles.

## Print and Chicago references

Option **7** now offers **1. Linked sources** or **4. Chicago references version**.
Both use a white background. Chicago export writes `encyclopedia-chicago.html`,
with numbered paragraph endnotes and an alphabetical bibliography, suitable for
printing or saving as PDF from a browser. It uses saved articles; no article regeneration is needed. Optional API reference
research is described below. CLI: `python3 -m sage export PROJECT --citations
chicago --output OUTPUT.html` (add `--partial` for an incomplete book).

Older source records contain only titles and URLs. These export as title-first web
references, not fully verified book/journal citations. The adjacent
`.citation-review.json` lists references that need metadata review. No authors,
publication dates, or access dates are invented. Generic titles such as "untitled"
still need editing. Chicago guidance: https://www.chicagomanualofstyle.org/tools_citationguide/citation-guide-1

Optional `citations.json` in the project maps source URLs to metadata objects with
`author`, `bibliography_author` (the formatted bibliography name), `title`, `site`,
`date`, and `accessed`. For books, journals, or other source types, supply complete
plain-text `note` and `bibliography` strings to override web formatting. These are
escaped safely; include their URL where appropriate. Export again to apply edits.

## API-assisted Chicago references

In option 7, choose Chicago and answer **y** to research missing reference metadata.
SAGE uses the project's selected model and web search to investigate each unique
cited URL without an author, then formats source-appropriate Chicago notes and
bibliography entries. Genuinely authorless sources remain authorless. Unresolved
lookups retain their saved references and stay in the citation-review report.
This is AI-assisted bibliographic research, not a guarantee of accuracy.

Set a lookup limit to work in batches; blank processes all uncached sources.
Each source normally requires one API request with web search and incurs charges.
`citation-cache.json` saves results after every source, so interruption/resuming
avoids repeating lookups. Unresolved lookups are cached too; remove a URL's cache
record to retry it. Manual `citations.json` overrides take precedence. Complete
manual note/bibliography pairs are not researched again.

CLI Chicago export performs lookups by default. `--citation-limit 25` limits new
lookups; `--offline-citations` uses only saved metadata and cached results. Other
exports never invoke reference research. No article regeneration is required.

## Export without references

Choose **7 → 3. No references** to export a clean reading edition to
`encyclopedia-no-references.html`. It omits citation markers, source lists,
endnotes, and the bibliography, while retaining the table of contents and article
navigation. Saved articles and source records remain unchanged. This export needs
no API calls. CLI: `python3 -m sage export PROJECT --citations none --output
encyclopedia-no-references.html` (add `--partial` for an incomplete volume).

## Four HTML editions

Option 7 offers: **1. Web**, **2. Kindle**, **3. No references**, and **4. Chicago references**.
Web retains its two-column desktop contents. Kindle uses a single column at all
screen sizes and in print, with simpler reflow-friendly sizing; this is HTML for
Kindle conversion, not an EPUB or KPF package. No references uses a single-column,
flush-left numbered contents list with each theme following its title on the same
line, with natural wrapping for long titles. Chicago retains reference research.

Files are `encyclopedia.html`, `encyclopedia-kindle.html`,
`encyclopedia-no-references.html`, and `encyclopedia-chicago.html`.
CLI: `python3 -m sage export PROJECT --edition kindle` (or `web`, `no-references`,
`chicago`). Existing `--citations` flags remain supported; `--edition` takes
precedence when both are supplied. Build still defaults to web.

All four option 7 exports default to partial draft: press Enter at the prompt to
export saved articles without requiring completion or a preface. Answer `n` to
require a complete book. CLI exports also default to partial; use `--complete`
for strict completeness. No-references editions continue to omit draft labels.

For long editorial guidance, save it as a UTF-8 plain-text file and enter
`@filename.txt` at the guidance prompt (for example, `@AI-guidance.txt`).
Absolute paths and paths containing spaces work too. The file's full contents
are stored in the project configuration, so it is not needed during generation.

## Word documents (.docx)

Install the optional Word exporter once, from the SAGE folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[word]"
```

In future terminal sessions, run `source .venv/bin/activate` before starting SAGE,
or launch directly with `.venv/bin/python -m sage`.

Open a project, choose **7. Export HTML or Word**, then **5. Word document (.docx)**.
Choose linked citations, no references, or Chicago references. The editable document
includes the current saved preface, single-column alphabetical contents with titles
only, and articles with Word heading styles. Linked citations remain superscript
links to sources. Partial export is the default. It uses saved articles without
regeneration; only optional Chicago metadata research calls the API.

```sh
python3 -m sage export AI --format docx
python3 -m sage export AI --format docx --edition no-references
python3 -m sage export AI --format docx --edition chicago --offline-citations
```

Default filenames are `encyclopedia.docx`, `encyclopedia-no-references.docx`, and
`encyclopedia-chicago.docx`. Use `--output` to choose another `.docx` filename.
HTML remains available without third-party packages.
