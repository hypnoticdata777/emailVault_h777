from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.api.app.domain.contracts import ApiError, ErrorCategory
from services.api.app.services.rendering.pdf import PdfRenderPolicy
from services.api.app.services.rendering.playwright_adapter import PlaywrightPdfRendererAdapter


class FakeRoute:
    def __init__(self) -> None:
        self.aborted = False

    def abort(self) -> None:
        self.aborted = True


class FakePage:
    def __init__(self) -> None:
        self.route_pattern: str | None = None
        self.route_handler = None
        self.html_content: str | None = None
        self.wait_until: str | None = None
        self.pdf_options: dict | None = None

    def route(self, pattern, handler) -> None:
        self.route_pattern = pattern
        self.route_handler = handler

    def set_content(self, html_content: str, wait_until: str) -> None:
        self.html_content = html_content
        self.wait_until = wait_until

    def pdf(self, **options) -> None:
        self.pdf_options = options
        Path(options["path"]).write_bytes(b"%PDF-1.4\n% fake playwright\n%%EOF")


class FakeContext:
    def __init__(self) -> None:
        self.javascript_enabled: bool | None = None
        self.page = FakePage()
        self.closed = False

    def new_page(self) -> FakePage:
        return self.page

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self) -> None:
        self.context = FakeContext()
        self.closed = False

    def new_context(self, **options) -> FakeContext:
        self.context.javascript_enabled = options["java_script_enabled"]
        return self.context

    def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(self) -> None:
        self.launch_options: dict | None = None
        self.browser = FakeBrowser()

    def launch(self, **options) -> FakeBrowser:
        self.launch_options = options
        return self.browser


class FakePlaywright:
    def __init__(self) -> None:
        self.chromium = FakeChromium()
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback
        self.exited = True


class PlaywrightRendererAdapterTests(unittest.TestCase):
    def test_adapter_disables_javascript_blocks_network_and_writes_pdf(self) -> None:
        fake_playwright = FakePlaywright()
        adapter = PlaywrightPdfRendererAdapter(
            playwright_factory=lambda: fake_playwright,
            chromium_launch_options={"headless": True},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "archive.pdf"
            adapter.render_pdf("<h1>Safe synthetic thread</h1>", output_path, PdfRenderPolicy())

        browser = fake_playwright.chromium.browser
        context = browser.context
        page = context.page
        route = FakeRoute()
        page.route_handler(route)

        self.assertTrue(fake_playwright.entered)
        self.assertTrue(fake_playwright.exited)
        self.assertEqual(fake_playwright.chromium.launch_options, {"headless": True})
        self.assertFalse(context.javascript_enabled)
        self.assertEqual(page.route_pattern, "**/*")
        self.assertTrue(route.aborted)
        self.assertEqual(page.html_content, "<h1>Safe synthetic thread</h1>")
        self.assertEqual(page.wait_until, "load")
        self.assertTrue(page.pdf_options["print_background"])
        self.assertTrue(page.pdf_options["prefer_css_page_size"])
        self.assertTrue(context.closed)
        self.assertTrue(browser.closed)

    def test_adapter_skips_route_when_network_blocking_disabled(self) -> None:
        fake_playwright = FakePlaywright()
        adapter = PlaywrightPdfRendererAdapter(playwright_factory=lambda: fake_playwright)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "archive.pdf"
            adapter.render_pdf("<p>Safe synthetic text</p>", output_path, PdfRenderPolicy(block_network=False))

        self.assertIsNone(fake_playwright.chromium.browser.context.page.route_pattern)

    def test_adapter_reports_missing_playwright_as_rendering_error(self) -> None:
        adapter = PlaywrightPdfRendererAdapter(playwright_factory=lambda: (_ for _ in ()).throw(ImportError("missing")))

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ApiError) as context:
                adapter.render_pdf("<p>Safe synthetic text</p>", Path(temp_dir) / "archive.pdf", PdfRenderPolicy())

        self.assertEqual(context.exception.category, ErrorCategory.SANITIZATION_RENDERING)


if __name__ == "__main__":
    unittest.main()
