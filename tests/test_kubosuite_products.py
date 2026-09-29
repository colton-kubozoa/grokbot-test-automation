"""KuboSuite product entries opened from the home page (Issue #6).

KuboDevelop, KuboSecure, and KuboOperate are separate pages. The overview links
KuboLib to /kubosuite/kubolib/, which is the public not-found page, so that
entry is asserted as the overview section that actually renders it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Locator, Page, ViewportSize, expect

KUBOSUITE_HEADING = re.compile(r"^KuboSuite(?:™)?$", re.I)
SEE_ALL_PRODUCTS = re.compile(r"^See all KuboSuite(?:™)? Products$")
OVERVIEW_PATH = "/kubosuite/"
VIEWPORT: ViewportSize = {"width": 1280, "height": 720}


@dataclass(frozen=True)
class ProductEntry:
    """One KuboSuite product a visitor can open from the products overview."""

    id: str
    link_name: re.Pattern[str]
    expect_path: str
    heading: re.Pattern[str]
    content: re.Pattern[str]
    # False when the linked URL is not a published page and the overview
    # section is the visitor-reachable destination.
    opens_page: bool = True


PRODUCTS: tuple[ProductEntry, ...] = (
    ProductEntry(
        id="kubodevelop",
        link_name=re.compile(r"^KuboDevelop(?:™)?$"),
        expect_path="/kubosuite/kubodevelop/",
        heading=re.compile(r"^KuboDevelop(?:™)?$"),
        content=re.compile(r"non-functional aspects of a microservice", re.I),
    ),
    ProductEntry(
        id="kubosecure",
        link_name=re.compile(r"^KuboSecure(?:™)?$"),
        expect_path="/kubosuite/kubosecure/",
        heading=re.compile(r"^KuboSecure(?:™)?$"),
        content=re.compile(r"Shift Security Left", re.I),
    ),
    ProductEntry(
        id="kubooperate",
        link_name=re.compile(r"^KuboOperate(?:™)?$"),
        expect_path="/kubosuite/kubooperate/",
        heading=re.compile(r"^KuboOperate(?:™)?$"),
        content=re.compile(r"move their workloads to the cloud", re.I),
    ),
    ProductEntry(
        id="kubolib",
        link_name=re.compile(r"^KuboLib(?:™)?$"),
        expect_path="/kubosuite/kubolib/",
        heading=re.compile(r"^KuboLib(?:™)?$"),
        content=re.compile(
            r"Reusable functions, utility packages and production grade microservices",
            re.I,
        ),
        opens_page=False,
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


def _load_home(page: Page, base_url: str, ctx: str) -> None:
    response = page.goto(base_url, wait_until="domcontentloaded")
    assert response is not None, f"[{ctx}] Expected a navigation response loading home"
    assert response.ok, f"[{ctx}] Expected HTTP success loading home, got status={response.status}"


def _assert_not_error_page(page: Page, ctx: str) -> None:
    title = page.title()
    lowered = title.lower()
    assert "404" not in lowered and "not found" not in lowered, (
        f"[{ctx}] Destination looks like an error page, title={title!r}"
    )


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
        f"[{ctx}] Expected a visible link {_label(name)} whose path is {expect_path!r} "
        f"(examined {count} name matches)"
    )


def _click(link: Locator, ctx: str) -> None:
    expect(link, f"[{ctx}] Expected the link to be visible before clicking").to_be_visible()
    link.evaluate("el => el.scrollIntoView({block: 'center', inline: 'nearest'})")
    link.click()


def _open_products_overview(page: Page, base_url: str, ctx: str) -> None:
    _load_home(page, base_url, ctx)
    link = _visible_link(page, SEE_ALL_PRODUCTS, OVERVIEW_PATH, ctx)
    _click(link, ctx)
    page.wait_for_load_state("domcontentloaded")
    assert _path(page.url) == _path(OVERVIEW_PATH), (
        f"[{ctx}] Expected the products overview path {OVERVIEW_PATH!r}, got {page.url!r}"
    )
    _assert_not_error_page(page, ctx)
    expect(
        page.get_by_role("heading", name=KUBOSUITE_HEADING).first,
        f"[{ctx}] Expected the products overview heading 'KuboSuite'",
    ).to_be_visible()


def _content(page: Page) -> Locator:
    return page.locator(".btContentWrap").first


@pytest.mark.parametrize("product", PRODUCTS, ids=[product.id for product in PRODUCTS])
def test_kubosuite_product_entry(
    page: Page,
    base_url: str,
    browser_name: str,
    product: ProductEntry,
) -> None:
    """Open one KuboSuite product from the overview and assert its destination."""
    if product.opens_page:
        action = f"from home, open See all KuboSuite Products, then open {product.id}"
        expectation = (
            f"page {product.expect_path} shows heading {_label(product.heading)} "
            f"and content {product.content.pattern!r}, and is not an error page"
        )
    else:
        action = f"from home, open See all KuboSuite Products, then read the {product.id} section"
        expectation = (
            f"overview section shows heading {_label(product.heading)} "
            f"and content {product.content.pattern!r} "
            f"(link path {product.expect_path} is not a published product page)"
        )

    page.set_viewport_size(VIEWPORT)
    ctx = _ctx(browser_name, base_url, action, expectation)
    _open_products_overview(page, base_url, ctx)

    content = _content(page)
    ctx_overview = _ctx(browser_name, page.url, action, expectation)
    link = _visible_link(content, product.link_name, product.expect_path, ctx_overview)

    if not product.opens_page:
        expect(
            link,
            f"[{ctx_overview}] Expected the {product.id} product entry link to be visible",
        ).to_be_visible()
        card = (
            content.locator("header.bt_bb_headline")
            .filter(has=page.get_by_role("link", name=product.link_name))
            .first
        )
        expect(
            card.get_by_role("heading", name=product.heading).first,
            f"[{ctx_overview}] Expected the {product.id} section heading",
        ).to_be_visible()
        expect(
            card.get_by_text(product.content).first,
            f"[{ctx_overview}] Expected the {product.id} section content "
            f"{product.content.pattern!r}",
        ).to_be_visible()
        return

    _click(link, ctx_overview)
    page.wait_for_load_state("domcontentloaded")
    ctx_after = _ctx(browser_name, page.url, action, expectation)
    assert _path(page.url) == _path(product.expect_path), (
        f"[{ctx_after}] Expected path {product.expect_path!r}"
    )
    _assert_not_error_page(page, ctx_after)
    expect(
        page.get_by_role("heading", name=product.heading).first,
        f"[{ctx_after}] Expected product heading {_label(product.heading)}",
    ).to_be_visible()
    expect(
        page.get_by_text(product.content).first,
        f"[{ctx_after}] Expected product content {product.content.pattern!r}",
    ).to_be_visible()
