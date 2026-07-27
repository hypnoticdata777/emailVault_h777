# Product Scope

Email Vault v0.2 is a Gmail offloader, inbox cleaner, and portable email export
tool. It helps a user save selected Gmail messages outside Gmail, organize those
exports by sender domain or user-selected category, and then optionally clean
Gmail according to explicit user rules.

The previous v0.1 foundation preserved one opened Gmail thread safely. That work
remains the preservation engine. The product direction now expands from a single
thread archive POC into a user-controlled email ferry: Gmail in, verified local
or synced storage out, optional inbox cleanup after verification.

## One-Line Pitch

Email Vault connects to Gmail, saves selected emails to storage you control, and
then cleans your inbox based on your rules so Gmail keeps the messages that need
your attention.

## Core User Problem

Busy users receive valuable newsletters, automated updates, bank notices, work
messages, receipts, research links, and personal communication faster than they
can sort it. They want to keep the information, but they do not want everything
living forever in their Gmail inbox or consuming Gmail storage.

The product must help users:

- keep copies of useful email outside Gmail;
- avoid losing newsletters, articles, receipts, and records;
- reduce inbox noise without manually filtering every sender;
- decide what Gmail should preserve, label, archive, trash, or leave alone;
- build a structured local knowledge folder that other tools can inspect later.

## Operating Modes

The modes are toggleable and can be combined. Every cleanup mode depends on the
same verified export package used by Preserve Mode.

1. Preserve Mode
   - Saves selected messages to local PC, USB drive, OneDrive-synced folder, or
     another configured storage target.
   - Gmail is not changed.

2. Clean Inbox Mode
   - Saves verified copies first.
   - Then applies optional Gmail actions such as label, archive, or mark-read.
   - This removes inbox noise but does not necessarily reduce Gmail storage,
     because archived Gmail still lives in Gmail.

3. Free Space Mode
   - Saves verified copies first.
   - Confirms checksums and export completeness.
   - Then moves selected Gmail messages to a trash/delete queue after explicit
     opt-in review.
   - This is the high-risk mode. It must include warnings, review screens, and a
     reversible window before permanent deletion where the platform allows it.

## What Gets Saved

Each exported email or thread should be able to produce a portable package:

- raw `.eml` email for portability;
- attachments in folders;
- metadata JSON with sender, sender domain, date, subject, labels, message id,
  thread id, classification, and export target;
- optional readable PDF or HTML copy;
- manifest and checksum file proving what was saved;
- optional normalized text/context file for search and downstream tools.

## Folder Organization

The user should be able to choose domain-based folders, predefined categories,
or a combination of both.

Example domain-first layout:

```text
EmailVault/
  nytimes.com/
    2026/
      07/
        message.eml
        metadata.json
        attachments/
  dev.to/
  substack.com/
  chase.com/
```

Example category-first layout:

```text
EmailVault/
  Newsletters/
    nytimes.com/
    substack.com/
  Banks/
    chase.com/
  Human/
  Needs-Review/
  Automated/
```

## Classification Targets

The first useful categories are:

- newsletters;
- automated/no-reply/system mail;
- banks and financial notices;
- real human messages;
- messages that need action or input;
- attachment-heavy messages;
- unknown or review-first messages.

Classification should start with transparent rules before advanced intelligence:
sender domain, sender address, newsletter headers, no-reply patterns, Gmail
labels/categories, attachment presence, and user overrides.

## AI And Data Port

Email Vault should not be locked to one AI product. It should create a clean
portable export port that a user can point at their own AI, search, knowledge
base, or research tool.

The AI/data port should expose folders and structured files that are easy for
other tools to read without needing direct Gmail access:

- normalized text;
- metadata JSON;
- manifests and checksums;
- attachment paths;
- sender-domain and category organization;
- clear provenance back to the source Gmail message or thread id.

## Included In The Public POC Direction

- Synthetic fixtures and public-safe demo data.
- Verified export package design.
- Local folder and removable-drive friendly storage target.
- Domain-based and category-based routing model.
- Review-first cleanup model.
- Preservation before Gmail mutation.
- Public documentation that makes archive, inbox cleanup, and free-space modes
  distinct.

## Deferred Until Private Validation

- Real Gmail mailbox batch processing.
- Real Gmail deletion or permanent delete behavior.
- Public hosted OAuth flow.
- Marketplace release.
- Cloud storage provider integrations beyond folder targets such as OneDrive
  sync folders.
- AI analysis, summaries, or generated replies inside Email Vault itself.

## Product Wording

Email Vault helps users export and organize email they control. It must not
claim legal-grade backup, byte-perfect Gmail replacement, guaranteed storage
reduction without deletion, or production-ready Gmail cleanup until those paths
are privately validated.
