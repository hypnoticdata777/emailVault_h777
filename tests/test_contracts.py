from __future__ import annotations

import io
import logging
import unittest
from dataclasses import replace
from uuid import UUID

from services.api.app.core.settings import Settings
from services.api.app.domain.contracts import ApiError, ErrorCategory, snapshot_fingerprint
from services.api.app.domain.state import assert_transition_allowed
from services.api.app.domain.contracts import ArchiveState
from services.api.app.services.audit.redaction import log_safe
from services.api.app.services.storage.paths import trusted_storage_name, validate_trusted_relative_path
from tests.fixture_loader import load_fixture


class ContractTests(unittest.TestCase):
    def test_plain_text_fixture_validates(self) -> None:
        load_fixture("plain_text").validate()

    def test_basic_html_fixture_validates(self) -> None:
        load_fixture("basic_html").validate()

    def test_missing_required_identifiers_fail_validation(self) -> None:
        request = load_fixture("plain_text")
        broken_thread = replace(request.thread, thread_id="")
        with self.assertRaises(ApiError) as raised:
            replace(request, thread=broken_thread).validate()
        self.assertEqual(raised.exception.category, ErrorCategory.INVALID_SCHEMA)

    def test_attachment_limits_are_enforced(self) -> None:
        with self.assertRaises(ApiError) as oversized:
            load_fixture("oversized_attachment").validate()
        self.assertEqual(oversized.exception.category, ErrorCategory.PAYLOAD_ATTACHMENT_LIMIT)

        request = load_fixture("plain_text")
        strict_settings = Settings(max_attachments=0)
        with self.assertRaises(ApiError) as too_many:
            request.validate(strict_settings)
        self.assertEqual(too_many.exception.category, ErrorCategory.PAYLOAD_ATTACHMENT_LIMIT)

    def test_unsupported_attachment_fails_with_controlled_error(self) -> None:
        with self.assertRaises(ApiError) as raised:
            load_fixture("unsupported_attachment").validate()
        self.assertEqual(raised.exception.category, ErrorCategory.UNSUPPORTED_ATTACHMENT)

    def test_storage_path_helper_rejects_untrusted_paths(self) -> None:
        generated = trusted_storage_name(UUID("00000000-0000-0000-0000-000000000001"), ".pdf")
        self.assertEqual(validate_trusted_relative_path(generated), generated)
        for bad_path in ("../secret.pdf", "C:\\secret.pdf", "/tmp/secret.pdf", "safe/secret.pdf", "safe\x00.pdf"):
            with self.subTest(bad_path=bad_path):
                with self.assertRaises(ApiError):
                    validate_trusted_relative_path(bad_path)

    def test_redaction_keeps_unique_fixture_phrase_out_of_logs(self) -> None:
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("email_vault_test_redaction")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False

        log_safe(logger, "archive requested", subject="UNIQUE_FIXTURE_SECRET_PHRASE", email="sender@example.com")

        output = stream.getvalue()
        self.assertNotIn("UNIQUE_FIXTURE_SECRET_PHRASE", output)
        self.assertNotIn("sender@example.com", output)

    def test_state_policy_rejects_gmail_finalization_before_completed(self) -> None:
        with self.assertRaises(ApiError):
            assert_transition_allowed(ArchiveState.RENDERED, ArchiveState.GMAIL_FINALIZATION_PENDING)
        with self.assertRaises(ApiError):
            assert_transition_allowed(ArchiveState.VERIFIED, ArchiveState.GMAIL_FINALIZATION_PENDING)
        assert_transition_allowed(ArchiveState.VERIFIED, ArchiveState.COMPLETED)
        assert_transition_allowed(ArchiveState.COMPLETED, ArchiveState.GMAIL_FINALIZATION_PENDING)
        assert_transition_allowed(ArchiveState.GMAIL_FINALIZATION_PENDING, ArchiveState.GMAIL_FINALIZED)
        assert_transition_allowed(
            ArchiveState.GMAIL_FINALIZATION_PENDING,
            ArchiveState.PRESERVED_GMAIL_FINALIZATION_FAILED,
        )

    def test_duplicate_fingerprint_is_deterministic_and_changes_for_revision(self) -> None:
        original = load_fixture("duplicate_snapshot").thread
        same_again = load_fixture("duplicate_snapshot").thread
        updated = load_fixture("updated_thread").thread

        self.assertEqual(snapshot_fingerprint(original), snapshot_fingerprint(same_again))
        self.assertNotEqual(snapshot_fingerprint(original), snapshot_fingerprint(updated))

    def test_fixtures_use_example_dot_com_data_only(self) -> None:
        for fixture in (
            "plain_text",
            "basic_html",
            "duplicate_snapshot",
            "updated_thread",
            "unsupported_attachment",
            "oversized_attachment",
            "malicious_html",
            "tracking_pixel",
            "path_traversal_filename",
        ):
            text = (load_fixture(fixture).thread.messages[0].from_participant.email)
            self.assertTrue(text.endswith("@example.com"))


if __name__ == "__main__":
    unittest.main()
