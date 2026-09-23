# duet-work

A library of skills for working with an AI assistant. Some of them belong to [Duet](https://github.com/alatyshau/duet), a human–AI operating environment; the rest work on their own.

Each skill is a folder under `skills/` with a `SKILL.md` in the Anthropic skill format, so it can be loaded by Claude Code, claude.ai and other clients that read that format.

## Skills

### `duet-chat`

Rules of conversation for the browser: every reply opens with a `## Response RX` header, its size is chosen by one of three routes (a multi-turn plan, a sectioned reply, or short prose under 200 words), and the text is connected, structured prose. Includes self-contained text, so a reply can be read without the chat history, and a running list of the chat's purposes.

### `duet-work`

`duet-chat` for Claude Code, plus a section on the work folder. The skill's argument is a path to a work folder: it sets the context of the chat and the place where results are saved, and it is not a task to report on. Covers business and work, project, process and program, tickets as alpha paths, and writing results to disk in time.

### `duet-setup-claude`

Know-how for tuning Claude Code and its VS Code extension: where the relevant files live, what can be changed, and what each change risks. Loaded only on request.

### `duet-work-full`

**Deprecated.** Kept as a source to mine; not for use. Described a conversation format with addressable thoughts and two root files of a work folder: `INDEX.md` kept by the agent, `NOTES.md` kept by the human.
