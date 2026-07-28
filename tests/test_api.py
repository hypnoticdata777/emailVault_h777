from __future__ import annotations

import base64
import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None


class FakePdfRendererAdapter:
    def render_pdf(self, html_content, output_path, policy) -> None:
        del html_content, policy
        output_path.write_bytes(b"%PDF-1.4 synthetic api route pdf")


class FakeAttachmentContentProvider:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def fetch_attachment_content(self, message, attachment) -> bytes:
        del message, attachment
        return self.content


@unittest.skipUnless(HAS_FASTAPI, "FastAPI/httpx are not installed")
class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient
        from services.api.app.api.dependencies import (
            get_addon_request_signature_verifier,
            get_attachment_content_provider,
            get_pdf_renderer_adapter,
            get_revision_repository,
            get_storage_provider,
        )
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
        self.attachment_provider_dependency = get_attachment_content_provider
        self.signature_verifier_dependency = get_addon_request_signature_verifier
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

    def test_demo_page_renders_synthetic_local_ui_without_auth(self) -> None:
        response = self.client.get("/demo")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Email Vault Synthetic Demo", response.text)
        self.assertIn("Gmail mutation disabled", response.text)
        self.assertIn("Example Daily Briefing", response.text)
        self.assertIn("Example Bank secure notice", response.text)
        self.assertIn("Synthetic ambiguous update", response.text)
        self.assertIn("python -m services.api.app.cli synthetic-demo", response.text)

    def test_demo_data_is_synthetic_read_only_and_mutation_disabled(self) -> None:
        response = self.client.get("/demo/data")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["mode"], "synthetic_web_demo")
        self.assertFalse(body["gmail_mutation_enabled"])
        self.assertFalse(body["writes_files"])
        self.assertEqual(body["summary"]["total_threads"], 3)
        self.assertEqual(body["summary"]["review_required_count"], 2)
        self.assertEqual(body["summary"]["approvable_count"], 1)
        self.assertEqual(
            body["summary"]["by_gmail_action"],
            {
                "label_mark_read_archive": 1,
                "needs_review": 2,
            },
        )
        self.assertEqual([item["category"] for item in body["items"]], ["newsletter", "bank_financial", "unknown"])
        self.assertEqual(body["items"][0]["intent_policy"], "eligible")
        self.assertEqual(body["items"][1]["intent_policy"], "held_for_review")

    def test_login_page_exposes_demo_and_admin_paths(self) -> None:
        response = self.client.get("/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Email Vault Access", response.text)
        self.assertIn("Demo Access", response.text)
        self.assertIn("Admin Access", response.text)

    def test_demo_login_redirects_to_synthetic_demo_without_gmail_access(self) -> None:
        with patch.dict("os.environ", {"EMAIL_VAULT_WEB_SESSION_SECRET": "test-session-secret"}):
            response = self.client.post("/login/demo", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/demo")
        self.assertIn("email_vault_session=", response.headers["set-cookie"])

    def test_admin_console_redirects_without_admin_session(self) -> None:
        response = self.client.get("/admin", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login")

    def test_admin_login_is_disabled_until_local_credentials_are_configured(self) -> None:
        with patch.dict("os.environ", {"EMAIL_VAULT_ADMIN_PASSWORD": "", "EMAIL_VAULT_WEB_SESSION_SECRET": ""}):
            response = self.client.post("/login/admin", data={"password": "owner-pass"}, follow_redirects=False)

        self.assertEqual(response.status_code, 503)
        self.assertIn("Admin login is disabled", response.text)

    def test_admin_login_sets_signed_session_cookie_and_opens_console(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "EMAIL_VAULT_ADMIN_PASSWORD": "owner-pass",
                "EMAIL_VAULT_WEB_SESSION_SECRET": "test-session-secret",
            },
        ):
            login_response = self.client.post("/login/admin", data={"password": "owner-pass"}, follow_redirects=False)
            admin_response = self.client.get("/admin")

        self.assertEqual(login_response.status_code, 303)
        self.assertEqual(login_response.headers["location"], "/admin")
        self.assertIn("email_vault_session=", login_response.headers["set-cookie"])
        self.assertEqual(admin_response.status_code, 200)
        self.assertIn("Email Vault Admin Console", admin_response.text)
        self.assertIn("Gmail OAuth", admin_response.text)
        self.assertIn("Token Storage", admin_response.text)
        self.assertIn("OAuth Readiness", admin_response.text)

    def test_admin_oauth_readiness_requires_admin_session(self) -> None:
        response = self.client.get("/admin/gmail/oauth/readiness", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login")

    def test_admin_oauth_readiness_reports_missing_private_config(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "EMAIL_VAULT_ADMIN_PASSWORD": "owner-pass",
                "EMAIL_VAULT_WEB_SESSION_SECRET": "test-session-secret",
                "GOOGLE_OAUTH_CLIENT_ID": "replace-with-google-oauth-client-id",
                "GOOGLE_OAUTH_CLIENT_SECRET": "",
            },
        ):
            self.client.post("/login/admin", data={"password": "owner-pass"}, follow_redirects=False)
            response = self.client.get("/admin/gmail/oauth/readiness")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["configured"])
        self.assertIn("GOOGLE_OAUTH_CLIENT_ID", body["missing"])
        self.assertIn("GOOGLE_OAUTH_CLIENT_SECRET", body["missing"])
        self.assertEqual(body["scopes"], ["https://www.googleapis.com/auth/gmail.readonly"])
        self.assertFalse(body["mutation_scopes_requested"])

    def test_admin_oauth_readiness_reports_read_only_config(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "EMAIL_VAULT_ADMIN_PASSWORD": "owner-pass",
                "EMAIL_VAULT_WEB_SESSION_SECRET": "test-session-secret",
                "GOOGLE_OAUTH_CLIENT_ID": "client-id.apps.googleusercontent.com",
                "GOOGLE_OAUTH_CLIENT_SECRET": "client-secret",
                "EMAIL_VAULT_OAUTH_REDIRECT_URI": "http://127.0.0.1:8000/oauth/google/callback",
                "EMAIL_VAULT_GMAIL_OAUTH_SCOPES": "https://www.googleapis.com/auth/gmail.readonly",
            },
        ):
            self.client.post("/login/admin", data={"password": "owner-pass"}, follow_redirects=False)
            response = self.client.get("/admin/gmail/oauth/readiness")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["configured"])
        self.assertEqual(body["missing"], [])
        self.assertTrue(body["authorization_url_available"])
        self.assertFalse(body["mutation_scopes_requested"])

    def test_admin_token_storage_readiness_requires_admin_session(self) -> None:
        response = self.client.get("/admin/gmail/token-storage/readiness", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login")

    def test_admin_token_storage_readiness_reports_missing_private_key(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "EMAIL_VAULT_ADMIN_PASSWORD": "owner-pass",
                "EMAIL_VAULT_WEB_SESSION_SECRET": "test-session-secret",
                "EMAIL_VAULT_TOKEN_STORE_PATH": ".local/email-vault-token-store.json",
                "EMAIL_VAULT_TOKEN_ENCRYPTION_KEY": "",
            },
        ):
            self.client.post("/login/admin", data={"password": "owner-pass"}, follow_redirects=False)
            response = self.client.get("/admin/gmail/token-storage/readiness")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["configured"])
        self.assertIn("EMAIL_VAULT_TOKEN_ENCRYPTION_KEY", body["missing"])
        self.assertFalse(body["stores_plaintext_tokens"])

    def test_oauth_callback_requires_admin_session(self) -> None:
        response = self.client.get("/oauth/google/callback?code=secret-code&state=state-123", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login")

    def test_oauth_callback_discards_authorization_code_until_token_exchange_exists(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "EMAIL_VAULT_ADMIN_PASSWORD": "owner-pass",
                "EMAIL_VAULT_WEB_SESSION_SECRET": "test-session-secret",
                "GOOGLE_OAUTH_CLIENT_ID": "client-id.apps.googleusercontent.com",
                "GOOGLE_OAUTH_CLIENT_SECRET": "client-secret",
                "EMAIL_VAULT_TOKEN_ENCRYPTION_KEY": "local-development-key",
            },
        ):
            self.client.post("/login/admin", data={"password": "owner-pass"}, follow_redirects=False)
            response = self.client.get("/oauth/google/callback?code=secret-code&state=state-123")

        self.assertEqual(response.status_code, 200)
        self.assertIn("OAuth Callback Received", response.text)
        self.assertIn("Authorization code was received and deliberately discarded", response.text)
        self.assertIn("Authorization code present: yes", response.text)
        self.assertNotIn("secret-code", response.text)

    def test_archive_requires_bearer_identity(self) -> None:
        response = self.client.post("/archive/thread", json=self._fixture("plain_text"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["category"], "authentication_authorization")

    def test_archive_preserves_snapshot_and_keeps_gmail_finalization_disabled(self) -> None:
        response = self._archive_fixture("plain_text")
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

    def test_gmail_finalization_route_returns_instructions_after_completed_archive(self) -> None:
        archive_response = self._archive_fixture("plain_text")
        record_id = archive_response.json()["record"]["record_id"]

        response = self.client.post(
            "/archive/thread/gmail-finalization",
            json={
                "record_id": record_id,
                "preferences": {
                    "category": "Receipts",
                    "mark_read_after_preserve": True,
                    "archive_after_preserve": True,
                },
            },
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["record"]["record_id"], record_id)
        self.assertTrue(body["gmail_finalization"]["enabled"])
        self.assertTrue(body["gmail_finalization"]["mark_read"])
        self.assertTrue(body["gmail_finalization"]["archive"])
        self.assertEqual(body["gmail_finalization"]["apply_label"], "EmailVault/Vaulted")

        audit_states = [event.state.value for event in self.repository.list_audit_events(record_id)]
        self.assertEqual(audit_states, ["RENDERED", "STAGED", "VERIFIED", "COMPLETED", "GMAIL_FINALIZATION_PENDING"])

    def test_gmail_finalization_callback_records_success_after_pending_request(self) -> None:
        archive_response = self._archive_fixture("plain_text")
        record_id = archive_response.json()["record"]["record_id"]
        self._request_gmail_finalization(record_id)

        response = self.client.post(
            "/archive/thread/gmail-finalization/callback",
            json={"record_id": record_id, "succeeded": True},
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["record"]["record_id"], record_id)
        self.assertEqual(body["state"], "GMAIL_FINALIZED")
        audit_states = [event.state.value for event in self.repository.list_audit_events(record_id)]
        self.assertEqual(
            audit_states,
            ["RENDERED", "STAGED", "VERIFIED", "COMPLETED", "GMAIL_FINALIZATION_PENDING", "GMAIL_FINALIZED"],
        )

    def test_gmail_finalization_callback_rejects_without_pending_request(self) -> None:
        archive_response = self._archive_fixture("plain_text")
        record_id = archive_response.json()["record"]["record_id"]

        response = self.client.post(
            "/archive/thread/gmail-finalization/callback",
            json={"record_id": record_id, "succeeded": True},
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["category"], "gmail_finalization")
        audit_states = [event.state.value for event in self.repository.list_audit_events(record_id)]
        self.assertEqual(audit_states, ["RENDERED", "STAGED", "VERIFIED", "COMPLETED"])

    def test_archive_accepts_matching_addon_request_signature_when_configured(self) -> None:
        from services.api.app.auth.request_signing import AddonRequestSignatureVerifier, sign_request

        payload = self._fixture("plain_text")
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = sign_request("shared-secret", "POST", "/archive/thread", "1000", body)
        self.app.dependency_overrides[self.signature_verifier_dependency] = lambda: AddonRequestSignatureVerifier(
            "shared-secret",
            now_factory=lambda: 1000,
        )

        response = self.client.post(
            "/archive/thread",
            data=body,
            headers={
                "Authorization": "Bearer synthetic-valid-token",
                "Content-Type": "application/json",
                "X-Email-Vault-Timestamp": "1000",
                "X-Email-Vault-Signature": signature,
            },
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "PRESERVED")

    def test_archive_rejects_unsigned_addon_request_when_configured(self) -> None:
        from services.api.app.auth.request_signing import AddonRequestSignatureVerifier

        self.app.dependency_overrides[self.signature_verifier_dependency] = lambda: AddonRequestSignatureVerifier(
            "shared-secret",
            now_factory=lambda: 1000,
        )

        response = self.client.post(
            "/archive/thread",
            json=self._fixture("plain_text"),
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["category"], "authentication_authorization")

    def test_archive_copies_trusted_permitted_attachment_when_provider_is_available(self) -> None:
        attachment_content = b"trusted api attachment bytes"
        payload = self._fixture("plain_text")
        payload["thread"]["messages"][0]["attachments"][0]["size_bytes"] = len(attachment_content)
        payload["thread"]["messages"][0]["attachments"][0]["content_sha256"] = hashlib.sha256(attachment_content).hexdigest()
        self.app.dependency_overrides[self.attachment_provider_dependency] = lambda: FakeAttachmentContentProvider(attachment_content)

        response = self.client.post(
            "/archive/thread",
            json=payload,
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["status"], "PRESERVED")
        self.assertEqual(body["verification"]["artifact_count"], 4)

    def test_archive_copies_trusted_attachment_bytes_from_payload(self) -> None:
        attachment_content = b"trusted payload attachment bytes"
        payload = self._fixture("plain_text")
        attachment = payload["thread"]["messages"][0]["attachments"][0]
        attachment["size_bytes"] = len(attachment_content)
        attachment["content_sha256"] = hashlib.sha256(attachment_content).hexdigest()
        attachment["trusted_content_base64"] = base64.b64encode(attachment_content).decode("ascii")

        response = self.client.post(
            "/archive/thread",
            json=payload,
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["status"], "PRESERVED")
        self.assertEqual(body["verification"]["artifact_count"], 4)

    def test_archive_rejects_trusted_attachment_payload_without_sha256(self) -> None:
        payload = self._fixture("plain_text")
        attachment = payload["thread"]["messages"][0]["attachments"][0]
        attachment["content_sha256"] = None
        attachment["trusted_content_base64"] = base64.b64encode(b"missing checksum").decode("ascii")

        response = self.client.post(
            "/archive/thread",
            json=payload,
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )

        self.assertEqual(response.status_code, 422)

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

    def _archive_fixture(self, name: str):
        return self.client.post(
            "/archive/thread",
            json=self._fixture(name),
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )

    def _request_gmail_finalization(self, record_id: str):
        return self.client.post(
            "/archive/thread/gmail-finalization",
            json={
                "record_id": record_id,
                "preferences": {
                    "category": "General",
                    "mark_read_after_preserve": False,
                    "archive_after_preserve": False,
                },
            },
            headers={"Authorization": "Bearer synthetic-valid-token"},
        )


if __name__ == "__main__":
    unittest.main()
