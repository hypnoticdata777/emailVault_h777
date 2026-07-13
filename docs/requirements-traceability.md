# Requirements Traceability

| Requirement | Phase | Current Test/Artifact |
| --- | --- | --- |
| Gmail unchanged before storage verification | P1/P6 | `test_state_policy_rejects_gmail_finalization_before_verified` |
| No completed partial archive | P2/P4 | State policy and ADR 0001 |
| Duplicate submissions reuse record | P1/P2 | `test_duplicate_fingerprint_is_deterministic_and_changes_for_revision` |
| Updated thread creates revision | P1/P2 | `updated_thread.json` and fingerprint test |
| Completed revisions immutable | P2 | Repository interface planned |
| Ownership from verified Google identity | P2 | Architecture doc |
| Sensitive data excluded from logs | P1 | `test_redaction_keeps_unique_fixture_phrase_out_of_logs` |
| No remote rendering fetches or JS | P3/P5 | Security fixtures and architecture doc |
| Temp files cleaned on success/failure | P4/P5 | Planned storage/rendering tests |
| Server-generated storage paths | P1 | `test_storage_path_helper_rejects_untrusted_paths` |
| Synthetic demo data only | P1 | Fixture policy and `test_fixtures_use_example_dot_com_data_only` |
| Attachment limits enforced | P1 | `test_attachment_limits_are_enforced` |
| Unsupported attachments controlled | P1 | `test_unsupported_attachment_fails_with_controlled_error` |
| Plain text and HTML fixtures validate | P1 | `test_plain_text_fixture_validates`, `test_basic_html_fixture_validates` |
| API requires verified identity boundary | P2 | `test_archive_requires_bearer_identity` |
| P2 route must not enable Gmail finalization | P2 | `test_archive_stub_validates_and_keeps_gmail_finalization_disabled` |
| Duplicate lookup is owner-scoped | P2 | `test_create_and_find_revision_by_snapshot_hash`, `test_same_snapshot_hash_can_exist_for_different_verified_owner` |
| Revision number increments per owner/thread | P2 | `test_next_revision_increments_per_owner_and_gmail_thread` |
| Audit state history is append-only ordered | P2 | `test_audit_events_are_appended_in_order` |
| Archive orchestration derives owner from verified identity | P2 | `test_duplicate_snapshot_returns_existing_record_without_gmail_finalization` |
| New P2 archive requests do not create unverified records | P2 | `test_new_snapshot_returns_controlled_failed_stub_without_writes` |
| Local API uses configured SQLite persistence | P2 | `test_archive_returns_duplicate_when_snapshot_already_exists`, `test_sqlite_path_is_derived_from_configured_database_url` |
| Project setup and API behavior are documented | P2 | `docs/development.md`, `docs/api.md`, `docs/data-model.md` |
