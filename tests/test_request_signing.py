from __future__ import annotations

import json
import unittest

from services.api.app.auth.request_signing import AddonRequestSignatureVerifier, sign_request
from services.api.app.domain.contracts import ApiError


class RequestSigningTests(unittest.TestCase):
    def test_sign_request_is_stable_for_canonical_request_parts(self) -> None:
        body = json.dumps({"thread": "example"}, separators=(",", ":")).encode("utf-8")

        signature = sign_request("shared-secret", "post", "/archive/thread", "1000", body)

        self.assertEqual(
            signature,
            "9657ebc8c3e50fffd6cb5e6c8314d1b9c5774399a15324a3a7990a250d52cd45",
        )

    def test_verifier_accepts_current_matching_signature(self) -> None:
        body = b'{"thread":"example"}'
        signature = sign_request("shared-secret", "POST", "/archive/thread", "1000", body)
        verifier = AddonRequestSignatureVerifier("shared-secret", now_factory=lambda: 1000)

        verifier.verify("POST", "/archive/thread", body, "1000", signature)

    def test_verifier_is_noop_when_secret_is_not_configured(self) -> None:
        verifier = AddonRequestSignatureVerifier("", now_factory=lambda: 1000)

        verifier.verify("POST", "/archive/thread", b"{}", None, None)

    def test_verifier_rejects_missing_headers_when_secret_is_configured(self) -> None:
        verifier = AddonRequestSignatureVerifier("shared-secret", now_factory=lambda: 1000)

        with self.assertRaises(ApiError):
            verifier.verify("POST", "/archive/thread", b"{}", None, None)

    def test_verifier_rejects_stale_timestamp(self) -> None:
        body = b"{}"
        signature = sign_request("shared-secret", "POST", "/archive/thread", "1000", body)
        verifier = AddonRequestSignatureVerifier("shared-secret", max_age_seconds=300, now_factory=lambda: 1401)

        with self.assertRaises(ApiError):
            verifier.verify("POST", "/archive/thread", body, "1000", signature)

    def test_verifier_rejects_modified_body(self) -> None:
        signature = sign_request("shared-secret", "POST", "/archive/thread", "1000", b'{"ok":true}')
        verifier = AddonRequestSignatureVerifier("shared-secret", now_factory=lambda: 1000)

        with self.assertRaises(ApiError):
            verifier.verify("POST", "/archive/thread", b'{"ok":false}', "1000", signature)


if __name__ == "__main__":
    unittest.main()
