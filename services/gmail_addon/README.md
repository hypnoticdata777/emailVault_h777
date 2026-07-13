# Gmail Workspace Add-on Shell

This folder contains the first preview-only Gmail Workspace Add-on shell for
Email Vault.

Current behavior:

- shows a homepage card when no Gmail thread is selected;
- shows a contextual card for the opened Gmail message/thread;
- collects category, mark-read preference, and archive preference;
- contains dormant helpers for signed backend archive request options;
- returns a local preview notification only.

The shell must not label, mark read, archive, delete, or otherwise mutate Gmail
until the backend has completed preservation and returned explicit finalization
instructions. Backend API calls, deployment configuration, and Marketplace
packaging are still later roadmap work.
