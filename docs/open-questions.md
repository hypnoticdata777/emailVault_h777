# Open Questions

Defaults from the master prompt are used unless an answer is required to proceed.

1. Which Google OAuth client ID will be used for the add-on?
   - Default for now: placeholder only in `.env.example`.
2. Should local development use SQLite files inside the repo or an external data
   directory?
   - Default for now: `sqlite:///./email_vault.db`.
3. Which deployment target should the API prepare for after P1?
   - Default for now: undecided; no deployment work in P0/P1.
4. Which storage provider should be used for demo beyond local filesystem?
   - Default for now: local configurable root; cloud provider deferred.
5. Should category values be free-form or controlled?
   - Default for now: free-form string, to avoid blocking contract work.

