![sage logo](sage-logo.png)

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

## Review decisions

Fact-checking separates blocking factual issues from editorial suggestions. Material
errors, unsupported central claims, invalid citations, and materially misleading
framing still block acceptance. Wording preferences and optional context are saved
as suggestions in `reviews/` and do not trigger retries. Revisions preserve
unflagged paragraphs and their citations; the synopsis changes only when flagged.
Follow-up reviews focus on corrections while still checking for material errors.

## Evidence and editorial quality

Each entry receives a web-researched evidence brief, a structured draft with paragraph-level source IDs, and a separate web-enabled fact-checking pass. At least two distinct cited source URLs are required; the reviewer is asked to check their independence and authority. Word counts exclude title, citations, and synopsis. Invalid length, missing citations, and failed evidence reviews trigger bounded drafting and review attempts; unresolved entries are retained as failures and excluded from publication. Failed fact-checks trigger targeted web research before the next draft. SAGE updates the evidence and adds cited sources while preserving source IDs. Separate format and fact-check retry limits apply; format/length failures do not trigger extra research. Terminal messages show research, drafting, and review progress. Concise failures link to full reports in `reviews/`; final issues are also saved in `errors/`, and corrective research in `research/`. Extra research incurs API and web-search charges.

The automated check is a model judgment, not proof of factual accuracy or source independence. SAGE cannot guarantee accuracy. A knowledgeable human editor should inspect claims and cited documents, especially contested history, cultural representation, and fast-changing information. A source URL's presence does not prove every associated assertion. Source guidance favors scholarship, scientific bodies, museums, official data, and community institutions.

The preface is based on synopses of **all accepted articles**, avoiding a single request containing 150,000–240,000 words. It synthesizes themes rather than repeating every entry. Any article change invalidates the saved preface. HTML escapes all generated text, includes no remote scripts or assets, supports print, and labels partial exports.

## Persistence, costs, and operation

- Project files: `config.json`, `ideas.json`, `entries/`, `research/`, `reviews/`, `errors/`, `preface.json`, `usage.jsonl`, and `encyclopedia.html`.
- Saves are atomic. A project lock prevents two local commands from modifying the same project simultaneously.
- Ctrl-C retains completed work. Rerun the command to resume; an interrupted entry may need to repeat its API calls.
- API calls incur your OpenAI API charges. A 300-entry volume normally needs 12 idea batches, at least 900 entry calls, and one preface call, plus revision/retry calls and web-search charges. Start with one entry to assess quality and usage. There is no built-in dollar budget; use API account spending controls and `--limit`.
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

Each article gets up to three format/length failures and three fact-check rounds,
with a maximum of six drafts. Format failures do not consume fact-check rounds.
The terminal displays the exact validation problem. After a limit or generation
error, SAGE saves the report, marks the article skipped, and continues.

Subsequent builds leave skipped articles for later. Option 4 shows their status;
option 5 with a specific entry ID retries one. The CLI `--retry-skipped` flag on
`generate` or `build` retries all skipped articles. Completed articles remain saved.

An incomplete build automatically exports accepted articles as a labeled partial
HTML draft, without generating a new preface. If no articles are accepted, it
reports that there is nothing to export. Skipped drafts stay in the review files
and are not labeled as accepted or included in the book.

## Faster standard mode

Choose option **11**, then **1** for standard mode. It makes one research call and
one writing call, with at most one additional writing attempt for missing citations
or malformed content. Word counts are guidance; there is no AI fact-check or
paragraph-preserving revision loop. Articles retain source links and HTML explicitly
labels the AI fact-check as skipped. Existing completed articles remain available.
Option 11 also offers strict mode. Existing projects without a mode keep strict
behavior until changed. CLI: `python3 -m sage mode PROJECT --mode standard`.

## License

Licensed under the [MIT License](LICENSE).

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
