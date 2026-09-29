"""Home-page smoke: load + branding, primary nav, and a main section."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

NAV_LABELS = ("What we do", "Who we are", "Join us", "Get in touch")
HERO_HEADING = re.compile(r"Cloud Native\.?\s*Streamlined\.?\s*Simplified", re.I)


def _ctx(browser_name: str, url: str) -> str:
    return f"browser={browser_name!r} url={url!r}"


def test_home_page_loads_with_key_content(
    page: Page, base_url: str, browser_name: str
) -> None:
    """Open home in the current browser and assert branding, nav, and a main section."""
    url = base_url
    ctx = _ctx(browser_name, url)
    response = page.goto(url, wait_until="domcontentloaded")

    assert response is not None, (
        f"[{ctx}] Expected a navigation response when loading the home page"
    )
    assert response.ok, (
        f"[{ctx}] Expected HTTP success loading home page, got status={response.status}"
    )

    title = page.title()
    assert "Kubozoa" in title, (
        f"[{ctx}] Expected page title to include brand name 'Kubozoa', got title={title!r}"
    )

    brand_logo = page.get_by_role("img", name="Kubozoa").first
    expect(
        brand_logo,
        f"[{ctx}] Expected Kubozoa branding logo (img alt='Kubozoa') to be visible",
    ).to_be_visible()

    navigation = page.get_by_role("navigation").first
    expect(
        navigation,
        f"[{ctx}] Expected a primary <nav> landmark on the home page",
    ).to_be_visible()

    for label in NAV_LABELS:
        link = navigation.get_by_role("link", name=label, exact=True).first
        expect(
            link,
            f"[{ctx}] Expected primary navigation link {label!r}",
        ).to_be_visible()

    main_section = page.get_by_role("heading", name=HERO_HEADING).first
    expect(
        main_section,
        f"[{ctx}] Expected main hero heading matching "
        f"'Cloud Native. Streamlined. Simplified'",
    ).to_be_visible()
