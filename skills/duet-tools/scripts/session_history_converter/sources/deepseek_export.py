"""Source: a DeepSeek share-page export, markdown.

'### User' / '### DeepSeek AI' role markers separate turns, but every assistant
body is HTML, not markdown: 'ds-markdown-paragraph' chrome, KaTeX spans,
code-block banners, and two shapes of thinking block. This module cleans
each assistant body to plain markdown before handing it to the shared
renderer. The cleanup logic (convert_katex, convert_tables,
strip_think_collapsible, deepseek_html_to_markdown) is a faithful port of a
previously working DeepSeek cleanup script; the ordering between its steps
is load-bearing (see the inline notes) and was worked out against real
exports, not guessed.

Caveat: this module has not been regression-tested against a real DeepSeek
export in this project (none exists here yet) — unlike claude_jsonl,
claude_export and google_export, which were checked byte-for-byte against
real material. Treat it as ported, reviewed logic, not verified output, and
diff its result against a real export the first time one is available.
"""

import re
import sys
from pathlib import Path

from turns import Atom

USER_MARKER = "### User"
AI_MARKER = "DeepSeek AI"
MARKER_LINE = re.compile(r"^### (User|DeepSeek AI)\s*$", re.MULTILINE)
LANG_LABEL_CLASS = "d813de27"  # class of the code-block language label as seen on real exports; drifts between builds

# --- HTML entity decoding (covers what DeepSeek realistically emits) -------
# DeepSeek escapes the structural characters (< > &) and the odd typographic
# entity; everything else it writes as literal Unicode. Numeric references
# are handled generally; named references via this table. An unlisted named
# reference is left as-is.
NAMED_ENTITIES = {
    "amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'", "nbsp": " ",
    "mdash": "—", "ndash": "–", "hellip": "…", "middot": "·",
    "laquo": "«", "raquo": "»", "lsquo": "‘", "rsquo": "’",
    "ldquo": "“", "rdquo": "”", "times": "×", "deg": "°",
    "copy": "©", "reg": "®", "trade": "™",
    "hairsp": " ", "thinsp": " ", "ensp": " ", "emsp": " ",
}
ENTITY_RE = re.compile(r"&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z][a-zA-Z0-9]*);")


def unescape_html(s: str) -> str:
    def repl(m: re.Match) -> str:
        body = m.group(1)
        if body[0] == "#":
            try:
                codepoint = int(body[2:], 16) if body[1] in "xX" else int(body[1:], 10)
                return chr(codepoint)
            except ValueError:
                return m.group(0)
        return NAMED_ENTITIES.get(body, m.group(0))

    return ENTITY_RE.sub(repl, s)


def detect(path: Path) -> bool:
    if path.suffix != ".md":
        return False
    text = path.read_text(encoding="utf-8")
    return bool(MARKER_LINE.search(text))


# --- converters --------------------------------------------------------------


def convert_katex(text: str) -> str:
    """Replaces each <span class="katex">...</span> with $<tex annotation>$.

    katex-html nests many same-class spans, so a non-greedy regex can't find
    the matching outer close — this scans span tags with a depth counter and
    pulls the LaTeX from the annotation node, discarding the visual subtree
    entirely. Must run before the generic span-strip, or the visual glyphs
    survive as garbled, doubled text.
    """
    open_tag = '<span class="katex">'
    span_re = re.compile(r"<span\b[^>]*>|</span>")
    annotation_re = re.compile(r'<annotation encoding="application/x-tex">([\s\S]*?)</annotation>')
    out = []
    i = 0
    while True:
        j = text.find(open_tag, i)
        if j == -1:
            out.append(text[i:])
            break
        out.append(text[i:j])
        depth = 1
        end = None
        pos = j + len(open_tag)
        for m in span_re.finditer(text, pos):
            depth += -1 if m.group(0).startswith("</span") else 1
            if depth == 0:
                end = m.end()
                break
        if end is None:
            out.append(text[j:])  # malformed -- bail
            break
        am = annotation_re.search(text, j, end)
        out.append("$" + (unescape_html(am.group(1)).strip() if am else "") + "$")
        i = end
    return "".join(out)


def convert_tables(text: str) -> str:
    """HTML <table> -> GitHub-flavored markdown table. Runs after
    convert_katex (so cells already hold $math$) and before the generic
    span-strip."""

    def render_table(m: re.Match) -> str:
        whole = m.group(0)
        rows = re.findall(r"<tr>([\s\S]*?)</tr>", whole)
        md = []
        for row in rows:
            cells = [
                re.sub(r"\s+", " ", unescape_html(re.sub(r"<[^>]+>", "", c)).strip())
                for c in re.findall(r"<t[hd][^>]*>([\s\S]*?)</t[hd]>", row)
            ]
            md.append("| " + " | ".join(cells) + " |")
        if md:
            ncol = md[0].count("|") - 1
            md.insert(1, "| " + " | ".join(["---"] * ncol) + " |")
        return "\n\n" + "\n".join(md) + "\n\n"

    return re.sub(r"<table>[\s\S]*?</table>", render_table, text)


def strip_think_collapsible(text: str) -> str:
    """Removes DeepSeek's collapsible reasoning block ("Thought for N
    seconds"). Distinct from the inline thinking-marker form: the opening
    turn's reasoning can instead arrive as two sibling top-level <div>s -- a
    clickable header and, separately, the expanded reasoning under a
    'ds-think-content' class. Both are dropped, keyed on that stable class
    and the header text -- never on the build-hash wrapper class, which
    drifts between DeepSeek revisions. Depth-aware div scan, since divs
    nest and a non-greedy regex can't find the match; identity transform
    when neither signal is present.
    """
    header_re = re.compile(r"Thought for\s+\d+\s+seconds?")

    def is_think(block: str) -> bool:
        return "ds-think-content" in block or bool(header_re.search(block))

    if not is_think(text):
        return text

    div_re = re.compile(r"<div\b[^>]*>|</div>")
    open_re = re.compile(r"<div\b[^>]*>")
    out = []
    i = 0
    while True:
        m = open_re.search(text, i)
        if m is None:
            out.append(text[i:])
            break
        out.append(text[i : m.start()])
        depth = 0
        end = None
        for mm in div_re.finditer(text, m.start()):
            depth += -1 if mm.group(0).startswith("</div") else 1
            if depth == 0:
                end = mm.end()
                break
        if end is None:
            out.append(text[m.start() :])  # malformed -- bail
            break
        block = text[m.start() : end]
        if not is_think(block):
            out.append(block)  # ordinary div -- keep it whole
        i = end
    return "".join(out)


def _convert_list(list_type: str, body: str) -> str:
    items = re.findall(r"<li>([\s\S]*?)</li>", body)
    out = []
    counter = 1
    for item in items:
        item = item.strip()
        item = re.sub(r"^<p[^>]*>", "", item)
        item = re.sub(r"</p>\s*$", "", item)
        item = re.sub(r"</p>\s*<p[^>]*>", "\n\n", item)
        item = re.sub(r"<p[^>]*>|</p>", "", item)
        prefix = f"{counter}. " if list_type == "ol" else "- "
        if list_type == "ol":
            counter += 1
        lines = item.strip().split("\n")
        if not lines:
            continue
        formatted = prefix + lines[0]
        for line in lines[1:]:
            formatted += "\n" if line.strip() == "" else "\n  " + line
        out.append(formatted)
    return "\n\n" + "\n".join(out) + "\n\n"


def deepseek_html_to_markdown(text: str) -> str:
    """Converts one DeepSeek assistant HTML body to markdown. Step order is
    load-bearing -- see the inline notes before reshuffling."""
    # 1. Drop thinking blocks (the model's reasoning, almost never wanted).
    #    Two shapes: the inline marker/blockquote form, and the collapsible
    #    "Thought for N seconds" div. Strip the div form first so its spans
    #    and SVG never reach the generic chrome sweep.
    text = strip_think_collapsible(text)
    text = re.sub(r"<p>\s*思考：\s*</p>\s*<blockquote>[\s\S]*?</blockquote>\s*<br\s*/?>", "", text)

    # 1a. KaTeX math -> $tex$ (before the generic span strip)
    text = convert_katex(text)

    # 1b. HTML tables -> markdown (cells may hold $math$; before span strip)
    text = convert_tables(text)

    # 2. Code blocks: the language label sits in its own <span>. Do not
    #    anchor on </div> right after </pre> -- it is not adjacent (Copy /
    #    Download SVG and div fragments sit between </pre> and the closing
    #    </div>).
    def render_code_block(m: re.Match) -> str:
        full, code = m.group(0), m.group(1)
        # The language label sits in a span whose class is a build hash. The
        # hash observed on real exports is tried first; if DeepSeek's build
        # has moved on, fall back to any hash-classed span whose content
        # looks like a language name rather than a button label.
        lang_m = re.search(rf'<span class="{LANG_LABEL_CLASS}">([^<]+)</span>', full) or re.search(
            r'<span class="[a-f0-9]{6,}">([A-Za-z0-9+#.-]{1,20})</span>', full
        )
        lang = lang_m.group(1).strip() if lang_m else ""
        stripped = re.sub(r"\s+$", "", unescape_html(re.sub(r"<[^>]+>", "", code)))
        return f"\n\n```{lang}\n{stripped}\n```\n\n"

    text = re.sub(r'<div class="md-code-block[^"]*">[\s\S]*?<pre[^>]*>([\s\S]*?)</pre>', render_code_block, text)

    # 2b. Fallback for any standalone <pre> not wrapped in a code-block div
    text = re.sub(
        r"<pre[^>]*>([\s\S]*?)</pre>",
        lambda m: "\n\n```\n" + re.sub(r"\s+$", "", unescape_html(re.sub(r"<[^>]+>", "", m.group(1)))) + "\n```\n\n",
        text,
    )

    # 3. Sweep UI chrome remnants left over from step 2
    text = re.sub(r"<svg[^>]*>[\s\S]*?</svg>", "", text)
    text = re.sub(r"<button[^>]*>[\s\S]*?</button>", "", text)
    text = re.sub(r"<path[^>]*/?>", "", text)
    text = re.sub(r"</?div[^>]*>", "", text)

    # 4. Empty span wrappers -- strip the tags, keep the content
    text = re.sub(r"<span[^>]*>", "", text)
    text = text.replace("</span>", "")

    # 5. Inline formatting
    text = re.sub(r"<strong>([\s\S]*?)</strong>", r"**\1**", text)
    text = re.sub(r"<em>([\s\S]*?)</em>", r"*\1*", text)

    # 6. <br> / <hr>
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<hr\s*/?>", "\n\n---\n\n", text)

    # 7. Shift heading levels (heading normalization downstream still
    #    applies on top of this; shifting here avoids an intermediate state
    #    where h2 sits directly under our own section heading)
    text = re.sub(r"<h2>([\s\S]*?)</h2>", r"\n\n### \1\n\n", text)
    text = re.sub(r"<h3>([\s\S]*?)</h3>", r"\n\n#### \1\n\n", text)
    text = re.sub(r"<h4>([\s\S]*?)</h4>", r"\n\n##### \1\n\n", text)

    # 8. Lists -- process innermost first, repeat until none are left
    list_pat = re.compile(r"<(ul|ol)(?:\s[^>]*)?>((?:(?!<(?:ul|ol)\b)[\s\S])*?)</\1>")
    while True:
        text, n = list_pat.subn(lambda m: _convert_list(m.group(1), m.group(2)), text)
        if n == 0:
            break

    # 9. Remaining <p>
    text = re.sub(r"<p[^>]*>", "", text)
    text = text.replace("</p>", "\n\n")

    # 10. Blockquote -> "> " prefix. Must run after lists/paragraphs (steps
    #     8-9) so a blockquote wrapping a list keeps it intact instead of
    #     spraying orphan "> " lines through raw HTML.
    def render_blockquote(m: re.Match) -> str:
        lines = [("> " + line if line.strip() else ">") for line in m.group(1).strip().split("\n")]
        collapsed: list[str] = []
        for line in lines:  # squeeze runs of empty quote lines
            if line == ">" and collapsed and collapsed[-1] == ">":
                continue
            collapsed.append(line)
        return "\n\n" + "\n".join(collapsed) + "\n\n"

    text = re.sub(r"<blockquote>([\s\S]*?)</blockquote>", render_blockquote, text)

    # 11. HTML entities and whitespace normalization
    text = unescape_html(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_atoms(path: Path) -> list[Atom]:
    text = path.read_text(encoding="utf-8")
    parts = MARKER_LINE.split(text)
    # parts[0] is whatever precedes the first marker; parts[1::2] are role
    # names; parts[2::2] are the raw bodies between markers.
    if parts[0].strip():
        sys.exit(f"unexpected content before the first role marker: {parts[0][:200]!r}")

    atoms: list[Atom] = []
    for role, raw_body in zip(parts[1::2], parts[2::2]):
        body = re.sub(r"\n*---\s*$", "", raw_body.strip()).strip()
        if role == AI_MARKER:
            if re.search(r"<[a-zA-Z]", body):
                body = deepseek_html_to_markdown(body)
            atoms.append(Atom("response", text=body))
        else:
            atoms.append(Atom("prompt", text=body))
    return atoms
