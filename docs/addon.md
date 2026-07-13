# Gmail Add-on Shell

The first Gmail Workspace Add-on shell lives in `services/gmail_addon/`.

Current files:

- `appsscript.json` declares the Workspace Add-on manifest, Gmail contextual
  trigger, homepage trigger, and current-message scopes.
- `Code.gs` builds a preview-only card for the selected Gmail message/thread.
  It also contains dormant helpers for building signed backend request options.
- `README.md` records the local boundary for the shell.

Current behavior:

- show a homepage card when no Gmail message is selected;
- show a contextual card when Gmail provides a selected message event;
- read selected-thread preview values when Gmail supplies a current-message
  access token;
- collect category, mark-read preference, and archive preference;
- return a local notification saying Gmail remains unchanged.

Current limits:

- no deployed Apps Script project is configured;
- no Marketplace listing or OAuth consent screen is configured;
- no backend API call is made from the add-on yet;
- signed request helpers exist, but they are not wired to `UrlFetchApp.fetch`;
- no Gmail label, mark-read, archive, delete, or undo behavior is implemented.

The shell is intentionally narrow. Gmail mutation must stay behind the backend
completion and finalization-instructions boundary.
