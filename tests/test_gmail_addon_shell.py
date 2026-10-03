from __future__ import annotations

import json
import unittest
from pathlib import Path


ADDON_ROOT = Path(__file__).parents[1] / "services" / "gmail_addon"


class GmailAddonShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads((ADDON_ROOT / "appsscript.json").read_text(encoding="utf-8"))
        self.source = (ADDON_ROOT / "Code.gs").read_text(encoding="utf-8")

    def test_manifest_declares_gmail_contextual_trigger(self) -> None:
        gmail_config = self.manifest["addOns"]["gmail"]
        triggers = gmail_config["contextualTriggers"]

        self.assertEqual(triggers[0]["onTriggerFunction"], "onGmailMessageOpen")
        self.assertEqual(triggers[0]["unconditional"], {})
        self.assertEqual(self.manifest["addOns"]["common"]["homepageTrigger"]["runFunction"], "onHomepage")

    def test_manifest_uses_minimal_current_message_scopes(self) -> None:
        scopes = set(self.manifest["oauthScopes"])

        self.assertIn("https://www.googleapis.com/auth/gmail.addons.current.message.metadata", scopes)
        self.assertIn("https://www.googleapis.com/auth/gmail.addons.current.message.readonly", scopes)
        self.assertIn("https://www.googleapis.com/auth/script.external_request", scopes)
        self.assertNotIn("https://mail.google.com/", scopes)
        self.assertNotIn("https://www.googleapis.com/auth/gmail.modify", scopes)

    def test_shell_exposes_preview_and_confirmation_entry_points(self) -> None:
        self.assertIn("function onHomepage()", self.source)
        self.assertIn("function onGmailMessageOpen(event)", self.source)
        self.assertIn("function archiveThreadAction(event)", self.source)
        self.assertIn("Prepare Archive", self.source)

    def test_shell_contains_signed_request_helpers(self) -> None:
        self.assertIn("function buildSignedArchiveRequestOptions_", self.source)
        self.assertIn("function signBackendRequest_", self.source)
        self.assertIn("X-Email-Vault-Timestamp", self.source)
        self.assertIn("X-Email-Vault-Signature", self.source)
        self.assertIn("Utilities.computeHmacSha256Signature", self.source)

    def test_shell_contains_gmail_finalization_helpers(self) -> None:
        self.assertIn("GMAIL_FINALIZATION_PATH", self.source)
        self.assertIn("GMAIL_FINALIZATION_CALLBACK_PATH", self.source)
        self.assertIn("function sendGmailFinalizationRequest_", self.source)
        self.assertIn("function sendGmailFinalizationCallback_", self.source)
        self.assertIn("function buildGmailFinalizationRequest_", self.source)
        self.assertIn("function buildGmailFinalizationCallback_", self.source)
        self.assertIn("/archive/thread/gmail-finalization", self.source)
        self.assertIn("/archive/thread/gmail-finalization/callback", self.source)

    def test_shell_wires_backend_call_behind_configuration(self) -> None:
        self.assertIn("function readBackendConfig_", self.source)
        self.assertIn("EMAIL_VAULT_BACKEND_URL", self.source)
        self.assertIn("EMAIL_VAULT_ADDON_SIGNING_SECRET", self.source)
        self.assertIn("ScriptApp.getIdentityToken()", self.source)
        self.assertIn("UrlFetchApp.fetch", self.source)
        self.assertIn("Backend is not configured. Gmail is unchanged.", self.source)

    def test_shell_builds_trusted_attachment_payload(self) -> None:
        self.assertIn("function buildArchiveThreadRequest_", self.source)
        self.assertIn("function buildMessageSnapshot_", self.source)
        self.assertIn("function buildAttachmentDescriptors_", self.source)
        self.assertIn("attachment.getBytes()", self.source)
        self.assertIn("trusted_content_base64", self.source)
        self.assertIn("Utilities.base64Encode(bytes)", self.source)
        self.assertIn("Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, bytes)", self.source)

    def test_shell_does_not_mutate_gmail(self) -> None:
        forbidden_calls = [
            ".addLabel(",
            ".archive(",
            ".delete",
            ".markRead(",
            ".markUnread(",
            ".moveToArchive(",
            ".moveToTrash(",
        ]

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, self.source)


if __name__ == "__main__":
    unittest.main()
