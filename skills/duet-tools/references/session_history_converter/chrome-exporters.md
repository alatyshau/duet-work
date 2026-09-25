# Chrome extensions for exporting web AI chats

A running catalog of browser extensions for exporting a chat from an AI
provider's web UI to a file. Primary use: someone asks how to export a chat
from Claude, ChatGPT, Gemini, Google AI Mode, or DeepSeek — answer with the
actual extension for that provider, by name and store link, from the list
below. Grown as new extensions turn up — this isn't meant to be exhaustive
on day one.

Secondary use, for work on this tool itself: each entry also gives the
export's output signature (so a file can be recognized even without knowing
which extension made it) and, where confirmed, which `sources/*.py` module
already parses that output.

## AI Chat Exporter

[Chrome Web Store](https://chromewebstore.google.com/detail/ai-chat-exporter/gnplifnbchmpeggocmkejocgldkahgnc)

Signs its output with a footer line, the last line of the file:

```
---
Exported by AI Chat Exporter on 9/17/2026, 11:55:57 PM from Google AI conversation
```

Confirmed to cover **Google Search AI Mode** — this is the actual source of
the `### AI Mode reply for ...` export format handled by
`sources/google_export.py` in this tool (confirmed against two real exports
that carry this exact footer). Which other AI services it supports isn't
recorded here yet.

## AI Chat Exporter: Save Claude as PDF, MD and more

[Chrome Web Store](https://chromewebstore.google.com/detail/ai-chat-exporter-save-cla/elhmfakncmnghlnabnolalcjkdpfjnin)

A different extension from the one above, despite the similar name — each
extension exports a different provider's chats, not one extension covering
several. This one is specifically for **claude.ai**. Signs its output with:

```
Powered by Claude Exporter (https://www.ai-chat-exporter.net)
```

This is the actual source of the `## User:` / `## Assistant:` export format
handled by `sources/claude_export.py` (confirmed against a real export that
carries this exact signature).

## ChatGPT Exporter - ChatGPT to PDF, MD, and more

[Chrome Web Store](https://chromewebstore.google.com/detail/chatgpt-exporter-chatgpt/ilmdofdhpnhffldihboadndccenlnfll)

For **ChatGPT**. No output signature or example on hand yet, so nothing
here is confirmed — matches the gap in `known-sources.md`, where
ChatGPT is listed as a source this tool doesn't parse yet, exactly because
no real export has been inspected. Fill in the signature and a `sources/`
module once one turns up.

## AI Chat Exporter: Gemini to PDF, MD and more

[Chrome Web Store](https://chromewebstore.google.com/detail/ai-chat-exporter-gemini-t/jfepajhaapfonhhfjmamediilplchakk)

For **Gemini** (the chat product, not Google Search AI Mode — a different
extension above already covers that one). Same publisher family as the
first two entries, one extension per provider again. No output signature or
example on hand yet; matches the Gemini gap in
`known-sources.md`.

## DeepSeek Chat Exporter

[Chrome Web Store](https://chromewebstore.google.com/detail/deepseek-chat-exporter/cohbpcihoiahgokbjkgkecodljploimg)

For **DeepSeek**. `sources/deepseek_export.py` already exists in this tool
and expects `### User` / `### DeepSeek AI` markers, but that module was
ported from an older tool and — as its own docstring says — has never been
checked against a real DeepSeek export in this project. No signature or
example from this specific extension is on hand yet either, so whether its
output actually matches what `deepseek_export.py` expects is still an open
question, not a confirmed link like the first two entries above.
