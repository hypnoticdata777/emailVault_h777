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
| Safe revision planning does not write completed records | P2 | `test_new_gmail_thread_gets_server_generated_vault_and_record_ids`, `test_updated_thread_reuses_existing_vault_thread_and_increments_revision` |
| Storage verifies artifacts before completion | P2/P4 | `test_stage_and_verify_copies_artifact_and_reports_verified_result`, `test_stage_and_verify_removes_partial_record_directory_on_checksum_failure` |
| Security and privacy boundaries are documented | P2 | `docs/security-and-privacy.md` |
| Sanitizer removes scripts and blocks remote tracking pixels | P3 | `test_malicious_html_removes_script_content_and_keeps_safe_text`, `test_tracking_pixel_blocks_remote_image_source` |
| Plain-text fallback is available for sanitized HTML | P3 | `test_plain_text_fallback_collapses_blocks` |
| Sanitized message bodies preserve safe text and produce fallback output | P3 | `test_html_message_normalization_adds_plain_text_fallback`, `test_plain_text_message_normalization_preserves_original_text` |
| Renderer input consumes sanitized bodies only | P3/P5 | `test_renderer_safe_snapshot_uses_sanitized_html_and_plain_text_fallback`, `test_renderer_safe_snapshot_preserves_plain_text_without_html` |
| Table-heavy and attachment-adjacent HTML is sanitized safely | P3 | `test_table_heavy_email_keeps_table_text_and_strips_unsafe_attributes`, `test_attachment_adjacent_file_link_loses_href_but_keeps_label`, `test_attachment_adjacent_data_link_loses_href_but_keeps_label` |
| Generated artifact names are server-owned before rendering/storage | P3/P4 | `test_plan_artifact_manifest_uses_generated_names_and_safe_snapshot_metadata`, `test_plan_artifact_manifest_rejects_untrusted_record_id` |
| PDF renderer must block network and email JavaScript | P3/P5 | `docs/adr/0003-pdf-renderer-boundary.md`, `test_render_pdf_uses_blocked_network_policy_and_returns_verified_bytes` |
| Renderer temporary workspace cleans up on failure | P3/P5 | `test_render_pdf_cleans_workspace_on_adapter_failure` |
| Playwright adapter configures safe browser rendering | P3/P5 | `test_adapter_disables_javascript_blocks_network_and_writes_pdf`, `test_adapter_skips_route_when_network_blocking_disabled` |
| Browser-backed PDF rendering has a local smoke-test path | P3/P5 | `test_real_playwright_adapter_renders_pdf_when_enabled` |
