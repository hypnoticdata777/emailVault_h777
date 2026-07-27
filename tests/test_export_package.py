from __future__ import annotations

import unittest
from uuid import UUID

from services.api.app.domain.contracts import ApiError, ArchiveRecordReference
from services.api.app.domain.export_package import (
    EXPORT_PACKAGE_SCHEMA_VERSION,
    ExportArtifactKind,
    ExportCategory,
    ExportFolderLayout,
    ExportPackageMode,
    ExportRoute,
    category_first_route,
    domain_first_route,
    normalize_route_segment,
    plan_export_package,
    validate_export_relative_parts,
)
from tests.fixture_loader import load_fixture


class ExportPackageSchemaTests(unittest.TestCase):
    def _reference(self, record_id: str = "record-export") -> ArchiveRecordReference:
        return ArchiveRecordReference(
            vault_thread_id="vault-thread-export",
            revision=3,
            record_id=record_id,
            snapshot_sha256="synthetic-export-sha256",
        )

    def test_plan_export_package_declares_portable_artifacts_and_cleanup_gate(self) -> None:
        request = load_fixture("plain_text")
        uuid_values = iter(
            (
                UUID("00000000-0000-0000-0000-000000000501"),
                UUID("00000000-0000-0000-0000-000000000502"),
                UUID("00000000-0000-0000-0000-000000000503"),
                UUID("00000000-0000-0000-0000-000000000504"),
                UUID("00000000-0000-0000-0000-000000000505"),
                UUID("00000000-0000-0000-0000-000000000506"),
                UUID("00000000-0000-0000-0000-000000000507"),
            )
        )

        package = plan_export_package(
            self._reference(),
            request.thread,
            domain_first_route("News.Example.COM", ExportCategory.NEWSLETTER),
            uuid_factory=lambda: next(uuid_values),
        )

        self.assertEqual(package.schema_version, EXPORT_PACKAGE_SCHEMA_VERSION)
        self.assertEqual(package.record_id, "record-export")
        self.assertEqual(package.gmail_thread_id, request.thread.gmail_thread_id)
        self.assertEqual(package.mode, ExportPackageMode.PRESERVE)
        self.assertFalse(package.cleanup_allowed)
        self.assertEqual(package.route.layout, ExportFolderLayout.DOMAIN_FIRST)
        self.assertEqual(package.route.relative_path, "news.example.com/newsletter")
        self.assertEqual(
            [(artifact.kind, artifact.trusted_name, artifact.content_type, artifact.required) for artifact in package.artifacts],
            [
                (
                    ExportArtifactKind.RAW_EML,
                    "00000000-0000-0000-0000-000000000501.eml",
                    "message/rfc822",
                    True,
                ),
                (
                    ExportArtifactKind.METADATA_JSON,
                    "00000000-0000-0000-0000-000000000502.metadata.json",
                    "application/json",
                    True,
                ),
                (
                    ExportArtifactKind.MANIFEST_JSON,
                    "00000000-0000-0000-0000-000000000503.manifest.json",
                    "application/json",
                    True,
                ),
                (
                    ExportArtifactKind.NORMALIZED_TEXT,
                    "00000000-0000-0000-0000-000000000504.txt",
                    "text/plain",
                    True,
                ),
                (
                    ExportArtifactKind.READABLE_HTML,
                    "00000000-0000-0000-0000-000000000505.html",
                    "text/html",
                    False,
                ),
                (
                    ExportArtifactKind.READABLE_PDF,
                    "00000000-0000-0000-0000-000000000506.pdf",
                    "application/pdf",
                    False,
                ),
                (
                    ExportArtifactKind.ATTACHMENT,
                    "00000000-0000-0000-0000-000000000507.pdf",
                    "application/pdf",
                    True,
                ),
            ],
        )

    def test_category_first_route_keeps_category_and_domain_as_separate_safe_folders(self) -> None:
        route = category_first_route("Alerts.Bank-Example.com", ExportCategory.BANK_FINANCIAL)

        self.assertEqual(route.layout, ExportFolderLayout.CATEGORY_FIRST)
        self.assertEqual(route.sender_domain, "alerts.bank-example.com")
        self.assertEqual(route.relative_parts, ("bank_financial", "alerts.bank-example.com"))
        route.validate()

    def test_clean_inbox_and_free_space_modes_are_cleanup_modes_after_export(self) -> None:
        request = load_fixture("basic_html")
        clean_package = plan_export_package(
            self._reference("record-clean"),
            request.thread,
            domain_first_route("newsletter.example.com"),
            mode=ExportPackageMode.CLEAN_INBOX,
        )
        free_space_package = plan_export_package(
            self._reference("record-free-space"),
            request.thread,
            domain_first_route("newsletter.example.com"),
            mode=ExportPackageMode.FREE_SPACE,
        )

        self.assertTrue(clean_package.cleanup_allowed)
        self.assertTrue(free_space_package.cleanup_allowed)

    def test_attachment_artifact_keeps_original_filename_as_metadata_only(self) -> None:
        request = load_fixture("plain_text")
        package = plan_export_package(
            self._reference(),
            request.thread,
            domain_first_route("receipts.example.com"),
        )

        attachment = package.artifacts[-1]
        self.assertEqual(attachment.kind, ExportArtifactKind.ATTACHMENT)
        self.assertEqual(attachment.source_message_id, "msg-plain-001")
        self.assertEqual(attachment.source_attachment_id, "att-plain-001")
        self.assertEqual(attachment.original_filename, "receipt.pdf")
        self.assertNotIn("receipt", attachment.trusted_name)

    def test_export_package_rejects_unsafe_record_id_and_route_parts(self) -> None:
        request = load_fixture("plain_text")

        with self.assertRaises(ApiError):
            plan_export_package(
                self._reference("../record-export"),
                request.thread,
                domain_first_route("news.example.com"),
            )

        with self.assertRaises(ApiError):
            validate_export_relative_parts(("safe", "../unsafe"))

        with self.assertRaises(ApiError):
            ExportRoute(
                layout=ExportFolderLayout.MIXED,
                category=ExportCategory.UNKNOWN,
                sender_domain="bad-domain",
                relative_parts=("safe/folder",),
            ).validate()

    def test_normalize_route_segment_removes_separators_without_returning_empty_segment(self) -> None:
        self.assertEqual(normalize_route_segment("  NYTimes / Daily\\Briefing  "), "nytimes-daily-briefing")
        with self.assertRaises(ApiError):
            normalize_route_segment(" / ")


if __name__ == "__main__":
    unittest.main()
