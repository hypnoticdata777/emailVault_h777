from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None


@unittest.skipUnless(HAS_FASTAPI, "FastAPI/httpx are not installed")
class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient
        from services.api.app.api.dependencies import get_revision_repository
        from services.api.app.domain.contracts import ArchiveRecordReference, snapshot_fingerprint
        from services.api.app.main import create_app
        from services.api.app.repositories.sqlite import SqliteRevisionRepository

        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = SqliteRevisionRepository(Path(self.temp_dir.name) / "api-test.db")
        self.app = create_app()
        self.app.dependency_overrides[get_revision_repository] = lambda: self.repository
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

    def test_archive_stub_validates_and_keeps_gmail_finalization_disabled(self) -> None:
        response = self.client.post(
            "/archive/thread",
            json=self._fixture("plain_text"),
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )
        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["status"], "FAILED")
        self.assertFalse(body["gmail_finalization"]["enabled"])
        self.assertEqual(body["error"]["category"], "unexpected_internal_error")

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
