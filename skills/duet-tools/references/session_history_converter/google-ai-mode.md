# Google AI Mode: converting a saved page

Read this when someone hands over a Google AI Mode thread saved from Chrome
— usually `<Title> - Google Search.html` in Downloads, with a `_files`
folder beside it — and names the chat's folder.

## Why the saved page and not the extension

The "AI Chat Exporter" extension (`sources/google_export.py`) writes no
dates at all and loses the formulas. The page itself shows the time of
every prompt and holds every turn up to the moment of saving, so Chrome's
**Save Page As → Web Page, Complete** is the better input
(`sources/google_saved_page.py`). "Webpage, HTML Only" does not work: it
saves the server's first HTML, before any turn has been rendered.

The saved page is ~18 MB, most of it stylesheets, scripts, and the side
panel with the person's whole search history, which must not land on the
synced drive. `slim_google_page.py` cuts it down to the turns (~0.7 MB) and
writes that copy into the chat's folder; the copy converts exactly like the
full page, so it is the original that is kept.

## Steps

1. Slim the page into the chat's folder:

   ```bash
   uv run --script scripts/session_history_converter/slim_google_page.py "<saved-page.html>" "<chat-folder>"
   ```

   "no AI Mode turns" means the page was saved as "HTML Only": ask for it to
   be saved again with **Save Page As → Web Page, Complete**, and stop.

2. Confirm the dates before converting. The page shows each prompt's time
   but no date, so the script dates the first prompt by the day the tab
   opened the thread, and prints that assumption with the resulting range.
   That is wrong whenever the chat began on an earlier day than the tab was
   opened, and nothing on the page can tell the two apart — so accept the
   printed date only when something independent agrees: a date the person
   gave, or the `YYMMDD` that starts the chat folder's name. With nothing to
   check against, or on a disagreement, ask on which day the chat began, and
   rerun step 1 with `--date YYYY-MM-DD`; that date is stored in the slim
   copy, so later conversions keep it.

   A new day is counted each time a prompt's time is earlier than the one
   before it, so a pause of a day or more between two prompts is invisible
   and every prompt after it comes out dated too early. When the script
   says the chat spans more than one day, tell the person so, with that
   caveat; if the dates turn out wrong, the script has no way yet to pin a
   later turn's date — that would be a change to it, made when needed.

3. Convert the slim copy:

   ```bash
   uv run --script scripts/session_history_converter/convert.py "<chat-folder>/<saved-page name>"
   ```

   Turn files it reports as stale are from an earlier run (a date fix
   renames them): delete those.

4. Say that the saved page and its `_files` folder in Downloads can now be
   deleted, and leave that to the person — they are outside the chat's
   folder and are theirs.
