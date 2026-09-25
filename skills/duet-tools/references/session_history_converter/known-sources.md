# Known but unimplemented sources

Marker patterns for AI chat exports this converter doesn't yet parse, carried
over from an older, narrower tool that handled them. Unlike `claude_jsonl`,
`claude_export`, `google_export` and `deepseek_export`, nothing here has been
implemented or tested against a real export — this is a starting point for
whoever adds the source next, not a promise that the format is exactly this.

## Gemini export

Sections `## Prompt:` / `## Response:`. No further detail is known about
dates, HTML in the body, or edge cases — inspect a real export before writing
a parser.

## ChatGPT export

Markdown export shape varies by exporter tool and has been observed as
`### You:` / `### ChatGPT:`, sometimes as bold markers (`**You:**` /
`**ChatGPT:**`) instead of headings. Treat this as a hint to grep for, not a
fixed format — check the actual file first:

```bash
grep -nE "^(### You:|### ChatGPT:|\*\*You:\*\*|\*\*ChatGPT:\*\*)" file.md | head -20
```

## General approach for adding one

1. Get a real export and inspect it: what marks a prompt vs. a response, is
   there a date, is the body plain markdown or HTML.
2. If the body is HTML, write a cleanup pass first (see `deepseek_export.py`
   for the shape one of these takes — depth-aware tag scanning where tags
   nest, KaTeX spans converted to `$...$` before any generic tag-stripping,
   blockquotes converted only after lists and paragraphs are already
   markdown).
3. Write `sources/<name>.py` exposing `detect(path)` and `load_atoms(path)`,
   register it in `convert.py`'s `SOURCES` list.
4. Regression-test against the real export before trusting the output —
   every implemented source in this tool was checked byte-for-byte against
   real material before being relied on.
