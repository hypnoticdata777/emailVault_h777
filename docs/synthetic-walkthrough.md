# Synthetic Walkthrough

This walkthrough is for portfolio, investor, and non-engineer review. It uses
only synthetic `example.com` fixtures and describes the intended user journey
without claiming live Gmail mutation or production backup behavior.

## One-Minute Story

Email Vault helps a busy Gmail user keep valuable email without letting every
newsletter, receipt, automated notice, or research link live forever in the
inbox.

The user chooses email to process, previews a dry run, exports verified copies
to storage they control, and only then can record cleanup intent. Live Gmail
label/archive/mark-read/delete actions remain disabled in the public POC.

Current local demo command:

```powershell
python -m services.api.app.cli local-batch --request tests/fixtures/emails/newsletter_digest.json --request tests/fixtures/emails/bank_notice.json --request tests/fixtures/emails/unknown_message.json --export-root .local/EmailVault --mark-read --record-approvable-intents --json
```

This command uses synthetic fixtures only. It writes verified local export
packages, previews Clean Inbox actions, and records intent only for lower-risk
approvable items while Gmail mutation remains disabled.

## Synthetic Demo Dataset

The public fixtures model six common email types:

| Fixture | Category | Why It Matters |
| --- | --- | --- |
| `newsletter_digest.json` | Newsletter | Represents articles, newsletters, and read-later content. |
| `automated_notice.json` | Automated | Represents no-reply/system messages that should not crowd the inbox. |
| `bank_notice.json` | Bank/financial | Represents sensitive mail that should require review. |
| `human_message.json` | Human | Represents messages from real people that likely need attention. |
| `attachments_heavy.json` | Attachments-heavy | Represents document-heavy mail that should be reviewed before cleanup. |
| `unknown_message.json` | Unknown | Represents ambiguous mail that defaults to review. |

All fixture addresses and content are invented. Real Gmail messages, OAuth
tokens, generated exports, and local databases must stay out of public Git.

## Walkthrough Flow

### 1. Connect And Preview

The user opens Email Vault from Gmail or a local interface and chooses a batch
of messages to review.

The current public code proves the backend safety boundaries that support this:

- verified identity boundary;
- signed add-on request boundary;
- canonical thread snapshot validation;
- duplicate detection;
- no Gmail mutation from the default archive route.

### 2. Classify And Route

Email Vault classifies each synthetic thread with deterministic rules before any
files are written.

Example dry-run output:

| Sender Domain | Category | Planned Export Path | Planned Gmail Action |
| --- | --- | --- | --- |
| `example.com` | newsletter | `example.com/newsletter` | `label_mark_read_archive` |
| `example.com` | automated | `example.com/automated` | `label_mark_read_archive` |
| `example.com` | bank_financial | `example.com/bank_financial` | `needs_review` |
| `example.com` | human | `example.com/human` | `needs_review` |
| `example.com` | attachments_heavy | `example.com/attachments_heavy` | `needs_review` |
| `example.com` | unknown | `example.com` | `needs_review` |

The important product behavior is review-first cleanup. Lower-risk newsletter
and automated mail can be prepared for cleanup review. Bank, human,
attachment-heavy, and unknown mail stay in review.

### 3. Export Verified Copies

In Preserve Mode, Email Vault writes a local export package under a safe
sender/category route:

```text
EmailVault/
  example.com/
    record-<server-generated-id>/
      <generated-id>.eml
      <generated-id>.metadata.json
      <generated-id>.txt
      <generated-id>.manifest.json
      <generated-id>.pdf
```

The exact filenames are server-generated. Original email subjects and original
attachment filenames are kept as metadata only and do not become storage paths.

The manifest records generated status, SHA-256 checksum, and byte size for the
package files. The archive coordinator records completion only after verified
output exists.

### 4. Record Clean Inbox Intent

After verified export, Clean Inbox Mode can record the user's desired Gmail
follow-up:

- apply Email Vault label;
- mark read if selected;
- archive if selected.

In the public POC, these instructions are returned with `enabled=false`.
That means intent is recorded for the future review/permission flow, but Gmail
is not changed.

### 5. Keep Free Space Deferred

Free Space Mode is intentionally not live. Trash/delete behavior requires:

- explicit opt-in;
- warning copy;
- dry-run review;
- verified export;
- reversibility window;
- private Gmail API validation.

The public POC must not claim Gmail storage reduction, because Gmail archive
alone does not free storage.

## Screenshot Checklist

Use this checklist for future synthetic screenshots or a portfolio page:

1. Product overview: "Gmail in, verified local export out, cleanup later."
2. Synthetic inbox batch: newsletter, automated, bank, human, attachment-heavy,
   and unknown examples.
3. Dry-run review table with category, sender domain, export path, and planned
   action.
4. Local export package folder showing generated filenames only.
5. Manifest JSON snippet showing checksums and generated status.
6. Clean Inbox intent screen showing label/archive/mark-read intent with Gmail
   mutation disabled.
7. Limitations screen: no real Gmail data, no live mutation, no delete/storage
   reduction claims.

## Public Demo Script

Use this short script when explaining the POC:

1. "The problem is inbox overload. Users want to keep valuable email but remove
   noise from Gmail."
2. "Email Vault first classifies and previews what would happen."
3. "Then it exports verified copies to storage the user controls."
4. "Only after verification does it record cleanup intent."
5. "The public POC deliberately does not mutate Gmail. That stays behind
   private OAuth, permissions, and live validation."

## What This Should Not Say

Do not present this POC as:

- a production Gmail backup;
- a legal hold system;
- a byte-perfect Gmail archive;
- a Gmail storage reducer;
- a live cleanup tool;
- an AI email-reading product.

The strong public claim is narrower and better: Email Vault demonstrates a
safety-first architecture for preserving email before any cleanup action.
