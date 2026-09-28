# Exporting web AI chats from Chrome

A running catalog of ways to get a chat out of an AI provider's web UI
into a file. Primary use: someone asks how to export a chat from Claude,
ChatGPT, Gemini, Google AI Mode, or DeepSeek — answer from the list below:
for Google AI Mode that is Chrome's own Save Page As, for the others the
actual extension for that provider, by name and store link. Grown as new
ways turn up — this isn't meant to be exhaustive on day one.

Secondary use, for work on this tool itself: each entry also gives the
export's output signature (so a file can be recognized even without knowing
which extension made it) and, where confirmed, which `sources/*.py` module
already parses that output.

## Google AI Mode: Save Page As — Web Page, Complete

No extension. In Chrome, on the AI Mode thread: **Save Page As → Web Page,
Complete**. This is the better export for AI Mode: it keeps the time of
every prompt, every turn up to the moment of saving, and the formulas — all
of which the extension below drops. `sources/google_saved_page.py` parses
the saved page; the page is large (~18 MB with its `_files` folder), so it
goes through a slim step first — see [google-ai-mode.md](google-ai-mode.md).

**Save Page As → Webpage, HTML Only** does not work: it saves the server's
first HTML, before any turn has been rendered.

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
that carry this exact footer). For AI Mode it is the fallback, not the
first choice: it drops the prompt times and the formulas, which the saved
page above keeps. Which other
AI services it supports isn't recorded here yet.

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
