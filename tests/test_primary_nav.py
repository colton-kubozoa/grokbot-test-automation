"""Primary navigation visitor flows from the home page (Issue #4)."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Locator, Page, expect

from result_store import CaseNote

# Match visible visitor labels; ™ may be present or omitted in accessible names.
KUBOSUITE_NAME = re.compile(r"KuboSuite(?:™)?", re.I)
SEE_ALL_PRODUCTS = re.compile(r"See all KuboSuite(?:™)? Products", re.I)


@dataclass(frozen=True)
class NavDestination:
    """One primary-nav (or equivalent in-site) destination under test."""

    id: str
    action: str
    expect_path: str
    heading: re.Pattern[str] | str
    open: Callable[[Page, Locator], None]


def _ctx(browser_name: str, url: str, action: str, expectation: str) -> str:
    return (
        f"browser={browser_name!r} url={url!r} "
        f"action={action!r} expectation={expectation!r}"
    )


def _primary_nav(page: Page) -> Locator:
    return page.get_by_role("navigation").first


def _open_top_level(page: Page, nav: Locator, label: str) -> None:
    del page
    nav.get_by_role("link", name=label, exact=True).first.click()


def _open_what_we_do_child(
    page: Page, nav: Locator, child_name: str | re.Pattern[str]
) -> None:
    del page
    parent = nav.get_by_role("link", name="What we do", exact=True).first
    parent.hover()
    child = nav.get_by_role("link", name=child_name).first
    expect(
        child,
        "Expected What we do submenu (or nav) link to become available",
    ).to_be_visible()
    child.click()


def _open_see_all_products(page: Page, nav: Locator) -> None:
    del nav  # in-site CTA on the home page, not a primary-nav item
    link = page.get_by_role("link", name=SEE_ALL_PRODUCTS).first
    expect(
        link,
        "Expected 'See all KuboSuite Products' in-site link on home",
    ).to_be_visible()
    link.click()


DESTINATIONS: tuple[NavDestination, ...] = (
    NavDestination(
        id="kubosuite-via-what-we-do",
        action="hover What we do → click KuboSuite",
        expect_path="/kubosuite/",
        heading=re.compile(r"^KuboSuite(?:™)?$", re.I),
        open=lambda page, nav: _open_what_we_do_child(page, nav, KUBOSUITE_NAME),
    ),
    NavDestination(
        id="services-via-what-we-do",
        action="hover What we do → click Services",
        expect_path="/services/",
        heading="Services",
        open=lambda page, nav: _open_what_we_do_child(page, nav, "Services"),
    ),
    NavDestination(
        id="who-we-are",
        action="click primary nav Who we are",
        expect_path="/who-we-are/",
        heading="Who we are",
        open=lambda page, nav: _open_top_level(page, nav, "Who we are"),
    ),
    NavDestination(
        id="join-us",
        action="click primary nav Join us",
        expect_path="/join-us/",
        heading="Join us",
        open=lambda page, nav: _open_top_level(page, nav, "Join us"),
    ),
    NavDestination(
        id="get-in-touch",
        action="click primary nav Get in touch",
        expect_path="/get-in-touch/",
        heading="Get in touch",
        open=lambda page, nav: _open_top_level(page, nav, "Get in touch"),
    ),
    NavDestination(
        id="kubosuite-products-overview",
        action="click See all KuboSuite Products",
        expect_path="/kubosuite/",
        heading=re.compile(r"^KuboSuite(?:™)?$", re.I),
        open=_open_see_all_products,
    ),
)


def _heading_expectation(heading: re.Pattern[str] | str) -> str:
    if isinstance(heading, re.Pattern):
        return f"heading matching {heading.pattern!r}"
    return f"heading {heading!r}"


@pytest.mark.parametrize(
    "destination",
    DESTINATIONS,
    ids=[d.id for d in DESTINATIONS],
)
def test_primary_nav_destination(
    page: Page,
    base_url: str,
    browser_name: str,
    destination: NavDestination,
    case_note: CaseNote,
) -> None:
    """From home, follow one primary-nav / in-site link and assert destination content."""
    home = base_url
    expectation = _heading_expectation(destination.heading)
    case_note.set(action=destination.action, expectation=expectation)
    ctx = _ctx(browser_name, home, destination.action, expectation)

    response = page.goto(home, wait_until="domcontentloaded")
    assert response is not None, f"[{ctx}] Expected a navigation response loading home"
    assert response.ok, (
        f"[{ctx}] Expected HTTP success loading home, got status={response.status}"
    )

    nav = _primary_nav(page)
    expect(nav, f"[{ctx}] Expected primary <nav> on home before navigation").to_be_visible()

    destination.open(page, nav)
    page.wait_for_load_state("domcontentloaded")

    current = page.url
    ctx_after = _ctx(browser_name, current, destination.action, expectation)
    expected_url = urljoin(base_url, destination.expect_path.lstrip("/"))
    assert destination.expect_path.rstrip("/") in current.rstrip("/"), (
        f"[{ctx_after}] Expected URL to include path {destination.expect_path!r} "
        f"(resolved {expected_url!r})"
    )

    title = page.title()
    assert "404" not in title.lower() and "not found" not in title.lower(), (
        f"[{ctx_after}] Destination looks like an error page, title={title!r}"
    )

    heading = page.get_by_role("heading", name=destination.heading).first
    expect(
        heading,
        f"[{ctx_after}] Expected destination to show {_heading_expectation(destination.heading)}",
    ).to_be_visible()
