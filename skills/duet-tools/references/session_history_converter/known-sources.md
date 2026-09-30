# Adding a source

Every export format this file used to list as known but unimplemented now
has a module: the Gemini and browser ChatGPT exports were added on
2026-09-29 as `sources/gemini_export.py` and `sources/chatgpt_export.py`,
each checked against a real export. The marker patterns carried over from
an older tool turned out wrong for them — the `## Prompt:` / `## Response:`
sections it attributed to Gemini are what ChatGPT Exporter writes, and the
Gemini export uses `## User:` / `## Gemini:` — which is why a real file
comes before any parser.

Local ChatGPT Code/Work rollout JSONL is a different thing from the browser
export and is handled by `sources/codex_jsonl.py`; see
[codex-sessions.md](codex-sessions.md).

## First check: is it another dialect of the exporter family?

claude.ai, ChatGPT and Gemini exports share one shape: a `# Title`, a
`**Exported:**` / `**Link:**` header, sections opened by a line such as
`## User:` / `## Assistant:`, a date line first in every section, and
sometimes a `Powered by ...` signature at the end. If a new export looks
like that, it is a `Dialect` in a small module over
`sources/exporter_family.py` — markers, date line, signature, and a
`split_response` that cuts out that provider's reasoning — not a new
parser. See `chatgpt_export.py` for a dialect whose reasoning block sits
after progress messages, `gemini_export.py` for the simplest one.

## General approach for anything else

1. Get a real export and inspect it: what marks a prompt vs. a response, is
   there a date, is the body plain markdown or HTML, how the model's
   reasoning is rendered and where the exporter signs the file.
2. If the body is HTML, write a cleanup pass first (see `deepseek_export.py`
   for the shape one of these takes — depth-aware tag scanning where tags
   nest, KaTeX spans converted to `$...$` before any generic tag-stripping,
   blockquotes converted only after lists and paragraphs are already
   markdown).
3. Write `sources/<name>.py` exposing `detect(path)` and `load_atoms(path)`,
   register it in `convert.py`'s `SOURCES` list — before any source whose
   `detect()` would also claim the file — and give it a `<Client>` label in
   `save.py`'s `CLIENT_BY_SOURCE`.
4. Regression-test against the real export before trusting the output —
   every implemented source in this tool was checked against real material
   before being relied on — and add small cases under
   `tests/session_history_converter/fixtures/<source>/`.
