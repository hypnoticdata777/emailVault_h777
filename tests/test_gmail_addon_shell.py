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

    def test_shell_contains_dormant_signed_request_helpers(self) -> None:
        self.assertIn("function buildSignedArchiveRequestOptions_", self.source)
        self.assertIn("function signBackendRequest_", self.source)
        self.assertIn("X-Email-Vault-Timestamp", self.source)
        self.assertIn("X-Email-Vault-Signature", self.source)
        self.assertIn("Utilities.computeHmacSha256Signature", self.source)
        self.assertNotIn("UrlFetchApp.fetch", self.source)

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
