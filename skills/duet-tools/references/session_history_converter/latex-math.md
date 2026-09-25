# Making math render: LaTeX / KaTeX fix-ups

Not implemented as code in this tool — this is a reference for a manual pass,
carried over from an older tool where it earned its keep. A converted turn
file is correct markdown, but some of its math still won't *render*: KaTeX
(the renderer behind most Markdown previews, including VS Code's) supports
only a subset of LaTeX, and assistants routinely emit things outside that
subset. Skip this entirely for a chat with no math.

Why this isn't automated here: the fixes below need judgment, not regex — a
`tikzcd` diagram has to be read and folded individually, not pattern-matched.
The general gate that gave this pass its teeth (`check_math.js`: mask code
blocks, render every `$...$`/`$$...$$` through KaTeX with `throwOnError`,
flag bare LaTeX sitting outside delimiters) also depended on the `katex` npm
package — a dependency this tool doesn't otherwise need. Reach for a
KaTeX-based check like that if this ever becomes a recurring, high-volume
need rather than an occasional manual fix.

## 1. Commutative diagrams: `tikzcd` -> KaTeX `CD`

Assistants draw commutative diagrams with `\begin{tikzcd}...\end{tikzcd}`,
usually with no `$$` delimiters at all. KaTeX cannot render `tikzcd` in any
form — wrapping it in `$$...$$` changes nothing. KaTeX does support the
AMScd `\begin{CD}...\end{CD}` environment (inside `$$...$$`); convert to that
instead.

### AMScd arrow cheat-sheet

| tikzcd | CD | meaning |
|---|---|---|
| `\ar[r, "f"]` | `@>{f}>>` | arrow right, label above |
| `\ar[r, "f"']` | `@>>{f}>` | arrow right, label below |
| `\ar[l, "f"]` | `@<{f}<<` | arrow left |
| `\ar[d, "f"]` | `@V{f}VV` | arrow down, label left |
| `\ar[d, "f"']` | `@VV{f}V` | arrow down, label right |
| `\ar[u, "f"]` | `@A{f}AA` | arrow up |
| identity edge (same object) | `@\|` vertical, `@=` horizontal | identity morphism |
| no arrow in a cell | `@.` | empty |

Columns are separated by the arrow tokens; rows by `\\`. Every grid position
is a node, including empty ones (`@.`).

### The hard constraint: `CD` has no diagonals and no spanning arrows

`tikzcd` freely draws diagonals (`\ar[rd]`, `\ar[ld]`) and arrows spanning
more than one cell (`\ar[rr]`, `\ar[dd]`). `CD` can do neither — every arrow
connects horizontally or vertically adjacent cells. Don't approximate; fold
the diagram into an equivalent commutative *square* by composing arrows
along an edge. A commutative diagram asserts an equation between composite
morphisms, so composing two arrows into one is faithful — it preserves
exactly what the diagram claims.

Three folding moves cover most cases:

- **Diagonal / triangle.** `A -f-> B`, `B -g-> C` (vertical), `A -h-> C`
  (diagonal) asserts `g∘f = h`. Render as a square with `h` on one side and
  an identity (`@|` / `@=`) closing the opposite side.
- **Three-column row that's really a composite.** `A -f-> B -g-> C` where
  the meaningful arrow is `g∘f` — collapse to `A -g∘f-> C`, dropping the
  middle node.
- **Two-row vertical span** (a `\ar[dd]` on one edge against a two-step
  column on the other) — collapse the two-step column into one composed
  arrow, producing a plain 2x2 square.

### Worked example (a monoid's associativity square, already a square)

```
$$
\begin{CD}
G \times G \times G @>{m \times \mathrm{id}}>> G \times G\\
@V{\mathrm{id} \times m}VV @VV{m}V\\
G \times G @>>{m}> G
\end{CD}
$$
```

A folded triangle (unit law), closing with an identity edge:

```
$$
\begin{CD}
1 \times G @>{\pi_2}>> G\\
@V{e \times \mathrm{id}}VV @|\\
G \times G @>>{m}> G
\end{CD}
$$
```

A malformed `CD` block fails silently in preview — converting isn't enough,
it has to parse. If a KaTeX-based checker is available, render every
`$$...$$` block through it after converting; otherwise, at minimum, preview
the file and confirm each diagram actually draws (KaTeX >= 0.16 has `CD`;
current VS Code ships a new-enough KaTeX).

## 2. Math glued to surrounding prose

Assistants sometimes drop the space after a closing delimiter, so the text
reads `...\mathcal{P}(G \times G \times G).$Then` with no separation. Inline
math needs a space or punctuation after the closing `$`; display math needs
blank lines around `$$...$$`. Add the missing whitespace so the sentence
reads — don't touch the LaTeX inside the delimiters.

## Fallback: composition equations

If a diagram resists `CD` even after folding, or diagrams aren't wanted,
render the same fact as a composition equality in display math instead — it
renders in any KaTeX/MathJax build:

```
$$m \circ (m \times \mathrm{id}) \;=\; m \circ (\mathrm{id} \times m)$$
```

Faithful and always renders, but it's a formula, not a drawn square. Prefer
a real `CD` diagram when the source had one; offer this when `CD` support is
in doubt.

## Anti-patterns

| Don't | Why |
|-------|-----|
| Wrap `tikzcd` in `$$...$$` and move on | KaTeX still can't render `tikzcd`. Convert to `CD` or an equation — delimiters alone change nothing |
| Approximate a diagonal with a straight `CD` arrow | Changes which composite is asserted equal. Fold by composition instead — that preserves the diagram's meaning |
| Batch-substitute `tikzcd` -> `CD` with one regex | Each diagram's layout (diagonals, spans) needs reading and folding individually; there is no universal token swap |
| Call the math done without rendering it | A malformed `CD` (or any other broken formula) fails silently in preview |
| Edit the LaTeX while fixing glued-text spacing | Spacing is formatting; the math content is the author's — only add the missing whitespace |
