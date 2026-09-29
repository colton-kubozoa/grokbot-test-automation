"""Footer destinations a visitor can open from the home page (Issue #6)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Locator, Page, ViewportSize, expect

VIEWPORT: ViewportSize = {"width": 1280, "height": 720}
KUBOSUITE_HEADING = re.compile(r"^KuboSuite(?:™)?$", re.I)


@dataclass(frozen=True)
class FooterDestination:
    """One in-site footer link. Hash-only and third-party social links are omitted."""

    id: str
    link_name: re.Pattern[str] | str
    expect_path: str
    heading: re.Pattern[str] | str
    content: re.Pattern[str]


# Same-site links inside .btSiteFooter. Address and email use href="#".
# Social icons leave the site (Facebook, X, Instagram, LinkedIn, GitHub, GitLab).
FOOTER_DESTINATIONS: tuple[FooterDestination, ...] = (
    FooterDestination(
        id="kubodevelop",
        link_name=re.compile(r"^KuboDevelop(?:™)?$"),
        expect_path="/kubosuite/kubodevelop/",
        heading=re.compile(r"^KuboDevelop(?:™)?$"),
        content=re.compile(r"non-functional aspects of a microservice", re.I),
    ),
    FooterDestination(
        id="kubosecure",
        link_name=re.compile(r"^KuboSecure(?:™)?$"),
        expect_path="/kubosuite/kubosecure/",
        heading=re.compile(r"^KuboSecure(?:™)?$"),
        content=re.compile(r"Shift Security Left", re.I),
    ),
    FooterDestination(
        id="kubooperate",
        link_name=re.compile(r"^KuboOperate(?:™)?$"),
        expect_path="/kubosuite/kubooperate/",
        heading=re.compile(r"^KuboOperate(?:™)?$"),
        content=re.compile(r"move their workloads to the cloud", re.I),
    ),
    FooterDestination(
        id="see-all-products",
        link_name=re.compile(r"^See all KuboSuite(?:™)? Products$"),
        expect_path="/kubosuite/",
        heading=KUBOSUITE_HEADING,
        content=re.compile(r"complementary products", re.I),
    ),
    FooterDestination(
        id="what-we-do",
        link_name="What we do",
        expect_path="/kubosuite",
        heading=KUBOSUITE_HEADING,
        content=re.compile(r"complementary products", re.I),
    ),
    FooterDestination(
        id="who-we-are",
        link_name="Who we are",
        expect_path="/who-we-are/",
        heading="Who we are",
        content=re.compile(r"Kubozoans", re.I),
    ),
    FooterDestination(
        id="join-us",
        link_name="Join us",
        expect_path="/join-us/",
        heading="Join us",
        content=re.compile(r"hiring process", re.I),
    ),
    FooterDestination(
        id="get-in-touch",
        link_name="Get in touch",
        expect_path="/get-in-touch/",
        heading="Get in touch",
        content=re.compile(r"Get in touch with us", re.I),
    ),
    FooterDestination(
        id="privacy-policy",
        link_name="Privacy Policy",
        expect_path="/privacy-policy/",
        heading="Privacy Policy",
        content=re.compile(r"Our website address is", re.I),
    ),
)


def _ctx(browser_name: str, url: str, action: str, expectation: str) -> str:
    return f"browser={browser_name!r} url={url!r} action={action!r} expectation={expectation!r}"


def _path(url: str) -> str:
    path = urlparse(url).path or url
    return path.rstrip("/") or "/"


def _label(name: re.Pattern[str] | str) -> str:
    if isinstance(name, re.Pattern):
        return f"matching {name.pattern!r}"
    return repr(name)


def _footer(page: Page) -> Locator:
    return page.locator(".btSiteFooter").first


def _visible_link(
    scope: Page | Locator,
    name: re.Pattern[str] | str,
    expect_path: str,
    ctx: str,
) -> Locator:
    if isinstance(name, str):
        links = scope.get_by_role("link", name=name, exact=True)
    else:
        links = scope.get_by_role("link", name=name)
    wanted = _path(expect_path)
    count = links.count()
    for index in range(count):
        candidate = links.nth(index)
        href = candidate.get_attribute("href") or ""
        if _path(href) != wanted:
            continue
        if candidate.is_visible():
            return candidate
    raise AssertionError(
        f"[{ctx}] Expected a visible footer link {_label(name)} whose path is {expect_path!r} "
        f"(examined {count} name matches)"
    )


def _assert_not_error_page(page: Page, ctx: str) -> None:
    title = page.title()
    lowered = title.lower()
    assert "404" not in lowered and "not found" not in lowered, (
        f"[{ctx}] Destination looks like an error page, title={title!r}"
    )


@pytest.mark.parametrize(
    "destination",
    FOOTER_DESTINATIONS,
    ids=[destination.id for destination in FOOTER_DESTINATIONS],
)
def test_footer_destination_from_home(
    page: Page,
    base_url: str,
    browser_name: str,
    destination: FooterDestination,
) -> None:
    """Follow one home-page footer link and assert the destination is usable."""
    action = f"from the home footer, open {destination.id}"
    expectation = (
        f"page {destination.expect_path} shows heading {_label(destination.heading)} "
        f"and content {destination.content.pattern!r}, and is not an error page"
    )
    page.set_viewport_size(VIEWPORT)
    ctx = _ctx(browser_name, base_url, action, expectation)

    response = page.goto(base_url, wait_until="domcontentloaded")
    assert response is not None, f"[{ctx}] Expected a navigation response loading home"
    assert response.ok, f"[{ctx}] Expected HTTP success loading home, got status={response.status}"

    footer = _footer(page)
    expect(footer, f"[{ctx}] Expected the home page footer to be present").to_be_visible()
    link = _visible_link(footer, destination.link_name, destination.expect_path, ctx)
    expect(link, f"[{ctx}] Expected the footer link to be visible before clicking").to_be_visible()
    link.evaluate("el => el.scrollIntoView({block: 'center', inline: 'nearest'})")
    link.click()
    page.wait_for_load_state("domcontentloaded")

    ctx_after = _ctx(browser_name, page.url, action, expectation)
    assert _path(page.url) == _path(destination.expect_path), (
        f"[{ctx_after}] Expected path {destination.expect_path!r}"
    )
    host = urlparse(page.url).netloc
    base_host = urlparse(base_url).netloc
    assert host == base_host, f"[{ctx_after}] Expected to stay on {base_host!r}, got host {host!r}"
    _assert_not_error_page(page, ctx_after)
    if isinstance(destination.heading, str):
        heading = page.get_by_role("heading", name=destination.heading, exact=True).first
    else:
        heading = page.get_by_role("heading", name=destination.heading).first
    expect(
        heading,
        f"[{ctx_after}] Expected destination heading {_label(destination.heading)}",
    ).to_be_visible()
    expect(
        page.get_by_text(destination.content).first,
        f"[{ctx_after}] Expected destination content {destination.content.pattern!r}",
    ).to_be_visible()
