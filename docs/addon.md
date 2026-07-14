# Gmail Add-on Shell

The first Gmail Workspace Add-on shell lives in `services/gmail_addon/`.

Current files:

- `appsscript.json` declares the Workspace Add-on manifest, Gmail contextual
  trigger, homepage trigger, and current-message scopes.
- `Code.gs` builds a card for the selected Gmail message/thread, prepares an
  archive payload with trusted attachment bytes, and can call the backend with
  signed request headers when script properties are configured.
- `README.md` records the local boundary for the shell.

Current behavior:

- show a homepage card when no Gmail message is selected;
- show a contextual card when Gmail provides a selected message event;
- read selected-thread preview values when Gmail supplies a current-message
  access token;
- collect category, mark-read preference, and archive preference;
- build an accessible snapshot of the selected Gmail thread;
- read permitted attachment bytes, compute SHA-256, and include base64 content
  for backend verification and copy;
- call `POST /archive/thread` with a Google identity token and HMAC signature
  only when backend URL and signing secret script properties are configured;
- return a notification saying Gmail remains unchanged.

Current limits:

- no deployed Apps Script project is configured;
- no Marketplace listing or OAuth consent screen is configured;
- backend API calls require `EMAIL_VAULT_BACKEND_URL` and
  `EMAIL_VAULT_ADDON_SIGNING_SECRET` script properties;
- attachment bytes are sent only inside the signed archive request payload;
- no Gmail label, mark-read, archive, delete, or undo behavior is implemented.

The shell is intentionally narrow. Gmail mutation must stay behind the backend
completion and finalization-instructions boundary.
