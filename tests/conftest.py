"""Shared Playwright fixtures for multi-browser smoke tests."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

DEFAULT_BASE_URL = "https://www.kubozoa.com/"
BROWSER_NAMES = ("chromium", "firefox", "webkit")
DEFAULT_TIMEOUT_MS = 15_000


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "browser(name): mark test result with the Playwright browser under test",
    )


@pytest.fixture(scope="session")
def base_url() -> str:
    """Configurable site root; override with BASE_URL (defaults to kubozoa.com)."""
    raw = os.environ.get("BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    return raw if raw.endswith("/") else f"{raw}/"


@pytest.fixture(scope="session")
def playwright_instance() -> Generator[Playwright]:
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session", params=BROWSER_NAMES, ids=BROWSER_NAMES)
def browser_name(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright, browser_name: str) -> Generator[Browser]:
    launcher = getattr(playwright_instance, browser_name)
    launched = launcher.launch(headless=True)
    yield launched
    launched.close()


@pytest.fixture
def page(browser: Browser) -> Generator[Page]:
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT_MS)
    page.set_default_navigation_timeout(DEFAULT_TIMEOUT_MS)
    yield page
    context.close()
