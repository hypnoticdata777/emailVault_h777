# Gmail Workspace Add-on Shell

This folder contains the first preview-only Gmail Workspace Add-on shell for
Email Vault.

Current behavior:

- shows a homepage card when no Gmail thread is selected;
- shows a contextual card for the opened Gmail message/thread;
- collects category, mark-read preference, and archive preference;
- builds an archive request payload with trusted attachment bytes;
- calls the backend with signed headers only when script properties are
  configured;
- requests Gmail finalization instructions after a preserved or duplicate
  backend result;
- includes a signed finalization callback helper for the later mutation step;
- returns a notification while keeping Gmail unchanged.

The shell must not label, mark read, archive, delete, or otherwise mutate Gmail
until the backend has completed preservation and returned explicit finalization
instructions. Deployment validation, live Gmail mutation execution, and
Marketplace packaging are still later roadmap work.
