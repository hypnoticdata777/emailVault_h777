# Requirements Traceability

| Requirement | Phase | Current Test/Artifact |
| --- | --- | --- |
| Gmail unchanged before storage verification | P1/P6 | `test_state_policy_rejects_gmail_finalization_before_completed` |
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
| Local synthetic identity remains explicit | P2/P6 | `test_dependency_defaults_to_synthetic_identity_verifier` |
| Google ID-token verifier validates configured client boundary | P6 | `test_google_verifier_accepts_verified_claims`, `test_dependency_selects_google_identity_verifier` |
| Misconfigured identity verifier fails closed | P6 | `test_google_verifier_rejects_placeholder_client_id_before_google_call`, `test_dependency_rejects_unknown_identity_verifier_mode` |
| P2 route must not enable Gmail finalization | P2/P6 | `test_archive_preserves_snapshot_and_keeps_gmail_finalization_disabled` |
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
| Rendered PDF output stages through storage without completion | P4/P5 | `test_stage_and_verify_rendered_pdf_writes_verified_storage_without_completion_state`, `test_stage_and_verify_rendered_pdf_cleans_temp_workspace_on_storage_failure` |
| Coordinator records verified storage without Gmail finalization | P4/P5 | `test_verified_storage_records_revision_and_verified_audit_without_gmail_finalization`, `test_unverified_storage_result_is_rejected_without_writes` |
| Coordinator completes only after verified storage | P5 | `test_completed_preservation_appends_completed_after_verified_storage`, `test_completed_preservation_requires_verified_state_without_writes` |
| Archive route can complete backend preservation without Gmail mutation | P6 | `test_preserve_new_snapshot_records_completed_archive_without_gmail_finalization`, `test_archive_preserves_snapshot_and_keeps_gmail_finalization_disabled` |
| Duplicate archive route requests return before rendering/storage | P6 | `test_preserve_duplicate_snapshot_returns_existing_record_without_rendering`, `test_archive_returns_duplicate_when_snapshot_already_exists` |
| Metadata and manifest artifacts are generated and staged with the PDF | P6 | `test_metadata_json_artifact_records_sanitized_thread_and_attachment_boundary`, `test_manifest_json_artifact_lists_generated_outputs_without_claiming_attachment_copy`, `test_stage_and_verify_generated_artifacts_writes_multiple_outputs` |
| Permitted attachment copy does not claim bytes before a trusted source exists | P6 | `test_metadata_json_artifact_records_sanitized_thread_and_attachment_boundary`, `test_manifest_json_artifact_lists_generated_outputs_without_claiming_attachment_copy` |
| Trusted permitted attachment bytes can be copied under server-generated names | P6 | `test_copy_artifacts_include_trusted_bytes_with_server_generated_name`, `test_preserve_new_snapshot_copies_trusted_permitted_attachment_bytes`, `test_archive_copies_trusted_permitted_attachment_when_provider_is_available` |
| Trusted attachment copy validates descriptor size and checksum | P6 | `test_copy_artifacts_reject_checksum_mismatch` |
| Gmail finalization starts only after completed preservation | P6 | `test_gmail_finalization_request_requires_completed_archive_and_returns_instructions`, `test_gmail_finalization_request_rejects_before_completed_without_writes` |
| Gmail finalization callback records only after pending state | P6 | `test_gmail_finalization_callback_records_success_after_pending_state`, `test_gmail_finalization_callback_rejects_without_pending_state` |
| Gmail finalization uses owner-scoped record lookup | P6 | `test_find_by_record_id_is_owner_scoped` |
| Stable test suite runs in CI | P6 | `.github/workflows/ci.yml` runs `python -m unittest discover -s tests` |
| Gmail Add-on shell has contextual entry point | P6 | `test_manifest_declares_gmail_contextual_trigger`, `services/gmail_addon/appsscript.json` |
| Gmail Add-on shell avoids broad mailbox scopes | P6 | `test_manifest_uses_minimal_current_message_scopes` |
| Gmail Add-on shell does not mutate Gmail | P6 | `test_shell_does_not_mutate_gmail` |
| Add-on archive requests can be signed before backend execution | P7 | `test_verifier_accepts_current_matching_signature`, `test_archive_accepts_matching_addon_request_signature_when_configured`, `test_shell_contains_signed_request_helpers` |
| Add-on archive execution requires deployment configuration | P7 | `test_shell_wires_backend_call_behind_configuration` |
| Add-on archive payload remains descriptor-only before attachment byte fetch | P7 | `test_shell_builds_descriptor_only_archive_payload` |
| Unsigned add-on archive requests fail when signing is configured | P7 | `test_archive_rejects_unsigned_addon_request_when_configured`, `test_verifier_rejects_missing_headers_when_secret_is_configured` |
| API runtime is packaged for container deployment | P7 | `test_dockerfile_packages_api_runtime`, `.github/workflows/ci.yml` Docker build step |
| API container runs as non-root and exposes healthcheck | P7 | `test_dockerfile_uses_non_root_user_and_healthcheck` |
| Runtime image excludes local secrets and non-runtime files | P7 | `test_dockerignore_excludes_local_secrets_and_non_runtime_files` |
