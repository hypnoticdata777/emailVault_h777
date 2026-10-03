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
| API exposes post-completion Gmail finalization instructions | P6 | `test_gmail_finalization_route_returns_instructions_after_completed_archive` |
| API records Gmail finalization callback only after pending request | P6 | `test_gmail_finalization_callback_records_success_after_pending_request`, `test_gmail_finalization_callback_rejects_without_pending_request` |
| Gmail finalization uses owner-scoped record lookup | P6 | `test_find_by_record_id_is_owner_scoped` |
| Stable test suite runs in CI | P6 | `.github/workflows/ci.yml` runs `python -m unittest discover -s tests` |
| Gmail Add-on shell has contextual entry point | P6 | `test_manifest_declares_gmail_contextual_trigger`, `services/gmail_addon/appsscript.json` |
| Gmail Add-on shell avoids broad mailbox scopes | P6 | `test_manifest_uses_minimal_current_message_scopes` |
| Gmail Add-on shell does not mutate Gmail | P6 | `test_shell_does_not_mutate_gmail` |
| Add-on archive requests can be signed before backend execution | P7 | `test_verifier_accepts_current_matching_signature`, `test_archive_accepts_matching_addon_request_signature_when_configured`, `test_shell_contains_signed_request_helpers` |
| Add-on archive execution requires deployment configuration | P7 | `test_shell_wires_backend_call_behind_configuration` |
| Add-on archive payload carries trusted attachment bytes for backend verification | P7 | `test_shell_builds_trusted_attachment_payload`, `test_archive_copies_trusted_attachment_bytes_from_payload`, `test_copy_artifacts_use_mapped_payload_bytes_before_fallback` |
| Add-on has signed Gmail finalization request/callback helpers | P7 | `test_shell_contains_gmail_finalization_helpers` |
| Unsigned add-on archive requests fail when signing is configured | P7 | `test_archive_rejects_unsigned_addon_request_when_configured`, `test_verifier_rejects_missing_headers_when_secret_is_configured` |
| API runtime is packaged for container deployment | P7 | `test_dockerfile_packages_api_runtime`, `.github/workflows/ci.yml` Docker build step |
| API container runs as non-root and exposes healthcheck | P7 | `test_dockerfile_uses_non_root_user_and_healthcheck` |
| Runtime image excludes local secrets and non-runtime files | P7 | `test_dockerignore_excludes_local_secrets_and_non_runtime_files` |
| Export package declares portable `.eml`, metadata, manifest, normalized text, readable copy, and attachment outputs | v0.2 | `test_plan_export_package_declares_portable_artifacts_and_cleanup_gate` |
| Export routing supports sender-domain and category-first folders with safe segments | v0.2 | `test_category_first_route_keeps_category_and_domain_as_separate_safe_folders`, `test_normalize_route_segment_removes_separators_without_returning_empty_segment` |
| Cleanup modes remain layered after verified export planning | v0.2 | `test_clean_inbox_and_free_space_modes_are_cleanup_modes_after_export` |
| Original attachment filenames stay metadata-only in export packages | v0.2 | `test_attachment_artifact_keeps_original_filename_as_metadata_only` |
| Export route planning derives sender-domain and category folder layouts before writing files | v0.2 | `test_plan_export_route_uses_primary_sender_domain_for_domain_first_layout`, `test_plan_export_route_supports_category_first_layout` |
| Export route planning supports user sender-domain overrides and review-first mixed routing | v0.2 | `test_plan_export_route_supports_sender_domain_override`, `test_mixed_layout_routes_review_first_categories_before_domain` |
| Export route planning rejects invalid sender domains | v0.2 | `test_normalize_sender_domain_rejects_invalid_domain` |
| v0.2 classifier seed fixtures cover newsletter, automated, bank, human, attachments-heavy, and unknown mail | v0.2 | `test_v0_2_classifier_seed_fixtures_validate` |
| Message headers can carry synthetic newsletter and automated classifier signals | v0.2 | `test_v0_2_classifier_seed_fixtures_include_expected_signals` |
| Deterministic classifier maps synthetic seed fixtures into export categories | v0.2 | `test_newsletter_fixture_classifies_from_list_headers_without_review`, `test_automated_fixture_classifies_from_headers_and_no_reply_sender_without_review`, `test_bank_fixture_classifies_as_review_required_financial_mail`, `test_human_fixture_classifies_as_review_required_human_mail`, `test_attachments_heavy_fixture_classifies_as_review_required_bulk_attachment_mail`, `test_unknown_fixture_defaults_to_review_required_unknown_mail` |
| Classifier rules expose evidence and keep risky categories review-required | v0.2 | `test_bank_fixture_classifies_as_review_required_financial_mail`, `test_no_reply_sender_wins_before_human_question_text` |
| Dry-run review reports category, sender, export path, and Gmail action counts before cleanup | v0.2 | `test_preserve_mode_summarizes_categories_routes_and_export_only_actions`, `test_clean_inbox_mode_holds_review_required_items_before_gmail_cleanup` |
| Free Space Mode dry-run does not plan direct Gmail deletion | v0.2 | `test_free_space_mode_never_plans_direct_delete_in_dry_run` |
| Local export package writer creates raw `.eml`, metadata, normalized text, attachment, and manifest outputs under safe route folders | v0.2 | `test_write_export_package_creates_required_files_and_checksum_manifest` |
| Local export package manifest records generated file checksums while original filenames remain metadata-only | v0.2 | `test_write_export_package_creates_required_files_and_checksum_manifest`, `test_metadata_keeps_original_attachment_filename_as_metadata_only` |
| Local export package writer rejects missing or mismatched trusted attachment bytes and cleans partial output | v0.2 | `test_missing_trusted_attachment_bytes_rejects_and_removes_partial_package`, `test_attachment_checksum_mismatch_rejects_and_removes_partial_package` |
| Preserve Mode can complete after verified local export package output without Gmail finalization | v0.2 | `test_preserve_export_package_writes_verified_local_package_without_gmail_finalization` |
| Preserve Mode local export package path short-circuits duplicates and rejects missing attachment bytes without state writes | v0.2 | `test_preserve_export_package_duplicate_returns_before_local_write`, `test_preserve_export_package_rejects_missing_attachment_bytes_without_state_writes` |
| Clean Inbox Mode intent records after completed export while Gmail mutation remains disabled | v0.2 | `test_clean_inbox_intent_records_after_completed_archive_without_mutation_enabled` |
| Clean Inbox Mode intent rejects pre-completion records and keeps finalization explicit | v0.2 | `test_clean_inbox_intent_rejects_before_completed_without_writes`, `test_gmail_finalization_can_still_be_explicitly_requested_after_clean_inbox_intent` |
| Local Preserve Mode CLI writes verified packages and reports safe status | v0.2 | `test_preserve_local_writes_package_and_prints_json_summary`, `test_preserve_local_duplicate_returns_existing_record_without_second_package` |
| Local Clean Inbox review CLI previews batch actions without Gmail mutation | v0.2 | `test_clean_inbox_review_prints_batch_plan_without_gmail_mutation`, `test_clean_inbox_review_accepts_sender_domain_override` |
| Local Clean Inbox intent CLI records completed-record intent without enabling Gmail mutation | v0.2 | `test_record_clean_inbox_intent_adds_audit_marker_without_enabling_gmail_mutation`, `test_record_clean_inbox_intent_rejects_unknown_or_unowned_record` |
| Local batch workflow preserves multiple requests, reviews cleanup, and records only approvable intents | v0.2 | `test_local_batch_preserves_reviews_and_records_only_approvable_intents`, `test_local_batch_without_intent_flag_preserves_and_reviews_only` |
| Local batch workflow can write public-safe Markdown output without absolute package paths | v0.2 | `test_local_batch_writes_public_safe_markdown_report` |
| Canonical synthetic demo command runs the public walkthrough and tolerates reruns | v0.2 | `test_synthetic_demo_runs_canonical_batch_with_short_command`, `test_synthetic_demo_can_be_rerun_after_approvable_intent_exists` |
| Read-only local web demo exposes synthetic review data without mutation or file writes | v0.2 | `test_demo_page_renders_synthetic_local_ui_without_auth`, `test_demo_data_is_synthetic_read_only_and_mutation_disabled` |
| Local web access separates public-safe demo from owner-only admin console | v0.2 | `test_login_page_exposes_demo_and_admin_paths`, `test_admin_console_redirects_without_admin_session`, `test_admin_login_sets_signed_session_cookie_and_opens_console` |
| Admin-only Gmail OAuth readiness reports private read-only setup before token exchange | v0.2 | `test_readiness_accepts_read_only_gmail_oauth_configuration`, `test_admin_oauth_readiness_reports_read_only_config` |
| OAuth callback exchanges authorization codes only after signed admin-state validation and encrypted token-storage readiness | v0.2 | `test_oauth_callback_rejects_authorization_code_with_invalid_state`, `test_oauth_callback_exchanges_code_and_stores_encrypted_token_after_state_check` |
| Token-storage readiness blocks plaintext token storage until a private key is configured | v0.2 | `test_token_storage_readiness_requires_encryption_key`, `test_admin_token_storage_readiness_reports_missing_private_key` |
