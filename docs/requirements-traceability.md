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

