from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None


@unittest.skipUnless(HAS_FASTAPI, "FastAPI/httpx are not installed")
class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient
        from services.api.app.main import create_app

        self.client = TestClient(create_app())
        self.fixture_root = Path(__file__).parent / "fixtures" / "emails"

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

