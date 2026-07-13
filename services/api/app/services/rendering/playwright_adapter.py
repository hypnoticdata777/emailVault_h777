from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from services.api.app.domain.contracts import ApiError, ErrorCategory
from services.api.app.services.rendering.pdf import PdfRenderPolicy


class PlaywrightPdfRendererAdapter:
    """Playwright-backed PDF renderer boundary.

    The adapter is isolated from the core renderer scaffold so standard-library
    tests can run without Playwright installed. Production wiring should provide
    the real `sync_playwright` factory through the default loader.
    """

    def __init__(
        self,
        playwright_factory: Callable[[], Any] | None = None,
        chromium_launch_options: Mapping[str, Any] | None = None,
    ) -> None:
        self.playwright_factory = playwright_factory
        self.chromium_launch_options = dict(chromium_launch_options or {})

    def render_pdf(self, html_content: str, output_path: Path, policy: PdfRenderPolicy) -> None:
        try:
            playwright_factory = self.playwright_factory or _load_sync_playwright()
            with playwright_factory() as playwright:
                browser = playwright.chromium.launch(**self.chromium_launch_options)
                try:
                    context = browser.new_context(java_script_enabled=policy.javascript_enabled)
                    try:
                        page = context.new_page()
                        if policy.block_network:
                            page.route("**/*", _abort_route)
                        page.set_content(html_content, wait_until="load")
                        page.pdf(path=str(output_path), print_background=True, prefer_css_page_size=True)
                    finally:
                        context.close()
                finally:
                    browser.close()
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError(ErrorCategory.SANITIZATION_RENDERING, "Playwright PDF rendering failed.", "pdf") from exc


def _load_sync_playwright() -> Callable[[], Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ApiError(
            ErrorCategory.SANITIZATION_RENDERING,
            "Playwright is not installed. Install the renderer optional dependencies before rendering PDFs.",
            "renderer",
        ) from exc
    return sync_playwright


def _abort_route(route: Any) -> None:
    route.abort()
