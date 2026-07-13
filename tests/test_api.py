from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None


class FakePdfRendererAdapter:
    def render_pdf(self, html_content, output_path, policy) -> None:
        del html_content, policy
        output_path.write_bytes(b"%PDF-1.4 synthetic api route pdf")


@unittest.skipUnless(HAS_FASTAPI, "FastAPI/httpx are not installed")
class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient
        from services.api.app.api.dependencies import get_pdf_renderer_adapter, get_revision_repository, get_storage_provider
        from services.api.app.domain.contracts import ArchiveRecordReference, snapshot_fingerprint
        from services.api.app.main import create_app
        from services.api.app.repositories.sqlite import SqliteRevisionRepository
        from services.api.app.services.storage.provider import LocalFilesystemStorageProvider

        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.repository = SqliteRevisionRepository(temp_path / "api-test.db")
        self.storage = LocalFilesystemStorageProvider(temp_path / "storage")
        self.app = create_app()
        self.app.dependency_overrides[get_revision_repository] = lambda: self.repository
        self.app.dependency_overrides[get_pdf_renderer_adapter] = lambda: FakePdfRendererAdapter()
        self.app.dependency_overrides[get_storage_provider] = lambda: self.storage
        self.client = TestClient(self.app)
        self.fixture_root = Path(__file__).parent / "fixtures" / "emails"
        self.archive_record_type = ArchiveRecordReference
        self.snapshot_fingerprint = snapshot_fingerprint

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _fixture(self, name: str) -> dict:
        return json.loads((self.fixture_root / f"{name}.json").read_text(encoding="utf-8"))

    def test_health_route(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_archive_requires_bearer_identity(self) -> None:
        response = self.client.post("/archive/thread", json=self._fixture("plain_text"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["category"], "authentication_authorization")

    def test_archive_preserves_snapshot_and_keeps_gmail_finalization_disabled(self) -> None:
        response = self.client.post(
            "/archive/thread",
            json=self._fixture("plain_text"),
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )
        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["status"], "PRESERVED")
        self.assertIsNotNone(body["record"])
        self.assertTrue(body["verification"]["verified"])
        self.assertEqual(body["verification"]["artifact_count"], 3)
        self.assertFalse(body["gmail_finalization"]["enabled"])
        self.assertIsNone(body["error"])

        audit_states = [event.state.value for event in self.repository.list_audit_events(body["record"]["record_id"])]
        self.assertEqual(audit_states, ["RENDERED", "STAGED", "VERIFIED", "COMPLETED"])

    def test_archive_returns_duplicate_when_snapshot_already_exists(self) -> None:
        payload = self._fixture("duplicate_snapshot")
        request_thread = payload["thread"]
        from tests.fixture_loader import load_fixture

        fingerprint = self.snapshot_fingerprint(load_fixture("duplicate_snapshot").thread)
        self.repository.create_revision(
            "google-subject-example",
            request_thread["gmail_thread_id"],
            self.archive_record_type(
                vault_thread_id="vault-thread-api-test",
                revision=1,
                record_id="record-api-test",
                snapshot_sha256=fingerprint,
            ),
        )

        response = self.client.post(
            "/archive/thread",
            json=payload,
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["status"], "DUPLICATE")
        self.assertEqual(body["record"]["record_id"], "record-api-test")
        self.assertFalse(body["gmail_finalization"]["enabled"])

    def test_archive_rejects_invalid_schema(self) -> None:
        payload = self._fixture("plain_text")
        payload["thread"]["thread_id"] = ""
        response = self.client.post(
            "/archive/thread",
            json=payload,
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
