---
name: duet-tools
description: Index of the Duet tool scripts and how to run them. Today one tool, the session history converter — turns an AI conversation (a local Claude Code or ChatGPT Code/Work session, or a claude.ai, ChatGPT, Gemini, Google AI Mode or DeepSeek export) into one markdown file per turn, and can file it as a dated, named folder wherever the person keeps their chats. Use it whenever a conversation is to be kept, converted, or someone asks how to export a chat, and when adding or changing a script in this skill.
disable-model-invocation: true
---

# Duet Tools

One tool, one folder under `scripts/`, always run as

```bash
uv run --script scripts/<tool>/<entry>.py ...
```

so that nothing gets installed next to the script on the synced drive. If `uv` is missing, tell the user the install command for their OS (`brew install uv` on macOS; the others are in [references/writing-a-tool.md](references/writing-a-tool.md)) and stop rather than working around it.

## Tools

### Session History Converter — `scripts/session_history_converter/`

Turns an AI conversation into one markdown file per human turn, in our own format, and can file it as a `<YYMMDD>_<HHMM>_<Client>_<Name>/` folder under whatever directory the person names — where chats are kept is their choice, not the tool's. Sources: local Claude Code sessions (by workspace) and Codex / ChatGPT Code/Work sessions (by title, session ID or workspace), claude.ai, ChatGPT and Gemini exports, Google AI Mode exports and saved pages, DeepSeek exports.

Reach for it when someone wants a conversation kept or converted, asks how to export a chat, or hands over such a file. Read [references/session_history_converter.md](references/session_history_converter.md) first: it lists the entry points with their flags and says which deeper guide to open for exporters, Google saved pages, new sources, or math that won't render.

## Adding or changing a script

Read [references/writing-a-tool.md](references/writing-a-tool.md) before writing: the script header `uv` needs, why no cache or environment may appear beside a script, the one line a multi-file tool must have before importing its siblings, and where tests go.
