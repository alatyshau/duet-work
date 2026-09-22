---
name: duet-setup-claude
description: Know-how for tuning Claude Code and its VS Code extension — where the relevant files live, what can be changed, and what each change risks. Load only when the user explicitly asks.
disable-model-invocation: true
---

# Duet — Claude Code setup

Know-how for configuring Claude Code as a tool: where its files live, what can
be changed there, and at what cost. Rules of conversation and work are out of
scope.

Each topic is a self-contained entry stamped with the date and version it was
verified against. If the installed version differs, check the facts on disk
before acting on them.

Anything that modifies files outside the user's workspace requires the user's
explicit consent, every time.

## VS Code extension

> Patches here modify the extension's bundled files. They are unofficial and
> unsupported, and they are lost on every extension update.

### Where it lives

`~/.vscode/extensions/anthropic.claude-code-<version>-<platform>/`
(`%USERPROFILE%\.vscode\extensions\` on Windows). Inside: `extension.js` — the
VS Code side — and `webview/` with `index.js` and `index.css` — the chat UI.

An update installs the new version into a sibling folder; the old one is listed
in `~/.vscode/extensions/.obsolete` and removed later, so both may coexist for a
while. Patch the newest one.

Changes under `webview/` take effect after **Developer: Reload Window**; the
chat history is re-rendered with the new styles.

*Verified 2026-09-22, version 2.1.280.*

### Spacing between paragraphs and list items

A recurring task: reapply after every extension update, with the user's
consent.

**Symptom.** Paragraphs in chat nearly run together. The gap between a
paragraph and a list looks right. List items have no gap at all.

**Cause.** In `webview/index.css`, the markdown root class (`.root_<suffix>`;
the suffix changes between builds) sets paragraphs to
`margin-top:.1em; margin-bottom:.2em`. Lists get no margins of their own, so
they fall back to the browser default of `1em`; list items get none.

**Fix.**

- Paragraphs: `1em` top and bottom, matching the list margin.
- Adjacent list items (`li + li`): `.2em` between them.
- Paragraphs inside a list item (`li > p`): `.1em`, so loose lists do not
  balloon.

Keep a copy of the original as `index.css.orig` next to it; to revert, put it
back and reload the window.

If the original rule is no longer there in the form described, the extension
has changed: investigate afresh rather than reapplying the fix blindly. After
patching, ask the user to reload the window and confirm the result visually,
for example with a screenshot of a reply containing two paragraphs and a list.

**Caveats.**

- The class is shared by all markdown in the chat, including thinking blocks.
- The last paragraph of a message also gets a `1em` bottom margin.
- Do not work around this from the assistant side, for example with blank
  lines made of non-breaking spaces: they pollute copied text.

*Verified 2026-09-22, version 2.1.280.*
