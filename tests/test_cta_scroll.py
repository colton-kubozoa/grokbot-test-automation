"""CTA clicks and scroll-through visitor interactions (Issue #5)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Locator, Page, ViewportSize, expect

from result_store import CaseNote

# Home hero; shared with the smoke test so a layout shift fails in the same place.
HERO_HEADING = re.compile(r"Cloud Native\.?\s*Streamlined\.?\s*Simplified", re.I)
KUBOSUITE_HEADING = re.compile(r"^KuboSuite(?:™)?$", re.I)
SEE_ALL_PRODUCTS = re.compile(r"^See all KuboSuite(?:™)? Products$", re.I)
# Body CTA is "Get In touch"; the primary nav link is "Get in touch" (Issue #4).
GET_IN_TOUCH_CTA = re.compile(r"^Get In touch$")
WHY_CHOOSE = re.compile(r"^Why Choose Kubozoa\??$", re.I)
READY_TO_START = "Ready to get started?"

# Desktop-sized viewport so below-the-fold assertions are stable across engines.
VIEWPORT: ViewportSize = {"width": 1280, "height": 720}
# Smaller than the viewport so a step cannot jump over a section heading.
SCROLL_STEP_PX = 400
MAX_SCROLL_STEPS = 30


@dataclass(frozen=True)
class HomeCta:
    """One in-page call to action a visitor can follow from home."""

    id: str
    action: str
    link_name: re.Pattern[str] | str
    expect_path: str
    heading: re.Pattern[str] | str
    content: re.Pattern[str]
    contact_form: bool = False


# Main home CTAs named in Issue #5. Product-detail and footer links stay out of scope.
HOME_CTAS: tuple[HomeCta, ...] = (
    HomeCta(
        id="more-about-us",
        action="show the hero slide, then click More about us",
        link_name="More about us",
        expect_path="/who-we-are/",
        heading="Who we are",
        content=re.compile(r"Kubozoans", re.I),
    ),
    HomeCta(
        id="learn-more",
        action="show the hero slide, then click Learn more",
        link_name="Learn more",
        expect_path="/kubosuite/",
        heading=KUBOSUITE_HEADING,
        content=re.compile(r"complementary products", re.I),
    ),
    HomeCta(
        id="read-more",
        action="show the hero slide, then click Read more",
        link_name="Read more",
        expect_path="/services/",
        heading="Services",
        content=re.compile(r"implementation services", re.I),
    ),
    HomeCta(
        id="view-open-positions",
        action="show the hero slide, then click View open positions",
        link_name="View open positions",
        expect_path="/join-us/",
        heading="Join us",
        content=re.compile(r"hiring process", re.I),
    ),
    HomeCta(
        id="see-all-kubosuite-products",
        action="click See all KuboSuite Products",
        link_name=SEE_ALL_PRODUCTS,
        expect_path="/kubosuite/",
        heading=KUBOSUITE_HEADING,
        content=re.compile(r"complementary products", re.I),
    ),
    HomeCta(
        id="get-in-touch",
        action="click Get In touch",
        link_name=GET_IN_TOUCH_CTA,
        expect_path="/get-in-touch/",
        heading="Get in touch",
        content=re.compile(r"Get in touch with us", re.I),
        contact_form=True,
    ),
)


def _ctx(browser_name: str, url: str, action: str, expectation: str) -> str:
    return f"browser={browser_name!r} url={url!r} action={action!r} expectation={expectation!r}"


def _heading_label(heading: re.Pattern[str] | str) -> str:
    if isinstance(heading, re.Pattern):
        return f"heading matching {heading.pattern!r}"
    return f"heading {heading!r}"


def _load_home(page: Page, base_url: str, ctx: str) -> None:
    response = page.goto(base_url, wait_until="domcontentloaded")
    assert response is not None, f"[{ctx}] Expected a navigation response loading home"
    assert response.ok, f"[{ctx}] Expected HTTP success loading home, got status={response.status}"


# Class token match. "slick-slider" contains the substring "slick-slide", so a
# bare contains() check would bind the slider root instead of the slide.
_SLIDE_XPATH = (
    "xpath=ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' slick-slide ')]"
)
_SLIDER_XPATH = (
    "xpath=ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' slick-slider ')]"
)


def _cta_link(page: Page, cta: HomeCta, ctx: str) -> Locator:
    """First visible home CTA whose href points at the expected section.

    Inactive hero slides are aria-hidden until selected, so the lookup includes
    hidden links and the caller reveals the slide before clicking.
    """
    if isinstance(cta.link_name, str):
        links = page.get_by_role("link", name=cta.link_name, exact=True, include_hidden=True)
    else:
        links = page.get_by_role("link", name=cta.link_name, include_hidden=True)
    path = cta.expect_path.rstrip("/")
    count = links.count()
    fallback: Locator | None = None
    for index in range(count):
        candidate = links.nth(index)
        href = candidate.get_attribute("href") or ""
        if path not in href:
            continue
        # Hero slides can still be fading in (opacity 0) when the link is found.
        if candidate.is_visible():
            return candidate
        if fallback is None:
            fallback = candidate
    if fallback is not None:
        return fallback
    label = cta.link_name.pattern if isinstance(cta.link_name, re.Pattern) else cta.link_name
    raise AssertionError(
        f"[{ctx}] Expected a CTA {label!r} linking to {cta.expect_path!r} "
        f"(examined {count} matching links)"
    )


def _pause_hero_autoplay(page: Page) -> None:
    """Stop the hero autoplay so a fade does not steal the click."""
    page.evaluate("""() => {
      const slider = document.querySelector(".slick-slider");
      if (!slider || !window.jQuery) {
        return;
      }
      const $slider = window.jQuery(slider);
      if ($slider.hasClass("slick-initialized")) {
        $slider.slick("slickPause");
      }
    }""")


def _wait_until_opaque(slide: Locator) -> None:
    slide.evaluate("""(el) => new Promise((resolve) => {
      const start = performance.now();
      const tick = () => {
        if (getComputedStyle(el).opacity === "1" || performance.now() - start > 2000) {
          resolve();
        } else {
          requestAnimationFrame(tick);
        }
      };
      tick();
    })""")


def _reveal_hero_slide(page: Page, link: Locator, ctx: str) -> None:
    """Select the hero slide that owns this CTA, when the link sits in the slider."""
    slides = link.locator(_SLIDE_XPATH)
    if slides.count() == 0:
        return
    slide = slides.first
    _pause_hero_autoplay(page)
    if slide.get_attribute("aria-hidden") != "false":
        raw_index = slide.get_attribute("data-slick-index")
        assert raw_index is not None and raw_index.lstrip("-").isdigit(), (
            f"[{ctx}] Expected the hero slide to expose data-slick-index, got {raw_index!r}"
        )
        index = int(raw_index)
        slider = slide.locator(_SLIDER_XPATH).first
        dot = slider.locator("ul.slick-dots").get_by_role("listitem").nth(index)
        expect(dot, f"[{ctx}] Expected hero slider dot {index + 1} to be visible").to_be_visible()
        dot.scroll_into_view_if_needed()
        dot.click()
        expect(
            slide,
            f"[{ctx}] Expected hero slide {index + 1} to become active before the CTA click",
        ).to_have_attribute("aria-hidden", "false")
    _wait_until_opaque(slide)


def _assert_not_error_page(page: Page, ctx: str) -> None:
    title = page.title()
    lowered = title.lower()
    assert "404" not in lowered and "not found" not in lowered, (
        f"[{ctx}] Destination looks like an error page, title={title!r}"
    )


def _assert_heading(page: Page, heading: re.Pattern[str] | str, ctx: str) -> None:
    if isinstance(heading, str):
        locator = page.get_by_role("heading", name=heading, exact=True).first
    else:
        locator = page.get_by_role("heading", name=heading).first
    expect(
        locator,
        f"[{ctx}] Expected destination to show {_heading_label(heading)}",
    ).to_be_visible()


def _assert_contact_form_usable(page: Page, ctx: str) -> None:
    """The contact form is on screen and editable. Do not enter personal data."""
    form = page.locator("form").first
    expect(form, f"[{ctx}] Expected the contact form to be visible").to_be_visible()

    fields = (
        ("name", page.get_by_placeholder(re.compile(r"Your Name", re.I)).first),
        ("email", page.get_by_placeholder(re.compile(r"Your Email", re.I)).first),
        ("message", page.get_by_placeholder(re.compile(r"Enter your Message", re.I)).first),
    )
    for label, field in fields:
        expect(field, f"[{ctx}] Expected contact form {label} field to be visible").to_be_visible()
        expect(field, f"[{ctx}] Expected contact form {label} field to be enabled").to_be_enabled()
        assert field.input_value() == "", (
            f"[{ctx}] Contact form {label} field was pre-filled; refusing to touch personal data"
        )

    submit = page.get_by_role("button", name=re.compile(r"^Submit message$", re.I)).first
    expect(submit, f"[{ctx}] Expected contact form submit control to be visible").to_be_visible()
    expect(submit, f"[{ctx}] Expected contact form submit control to be enabled").to_be_enabled()


def _box_top(locator: Locator, ctx: str) -> float:
    box = locator.bounding_box()
    assert box is not None, f"[{ctx}] Expected element to have a layout box"
    return float(box["y"])


def _intersects_viewport(locator: Locator, viewport_height: int) -> bool:
    box = locator.bounding_box()
    if box is None:
        return False
    top = float(box["y"])
    bottom = top + float(box["height"])
    return bottom > 0 and top < viewport_height


def _visible_heading(page: Page, name: re.Pattern[str] | str, ctx: str) -> Locator:
    headings = page.get_by_role("heading", name=name)
    count = headings.count()
    for index in range(count):
        candidate = headings.nth(index)
        if candidate.bounding_box() is not None:
            return candidate
    raise AssertionError(f"[{ctx}] Expected a laid-out heading {name!r} (examined {count})")


def _scroll_down(page: Page, distance: int) -> None:
    """Advance the document by a fixed distance.

    Wheel deltas differ by engine and can jump past a section in one gesture, so
    the scroll-through uses document scrolling in viewport-sized steps.
    """
    page.evaluate("(dy) => window.scrollBy(0, dy)", distance)


@pytest.mark.parametrize("cta", HOME_CTAS, ids=[cta.id for cta in HOME_CTAS])
def test_home_cta_reaches_expected_content(
    page: Page,
    base_url: str,
    browser_name: str,
    cta: HomeCta,
    case_note: CaseNote,
) -> None:
    """Follow one home-page CTA and assert the destination loaded with expected content."""
    expectation = f"{_heading_label(cta.heading)} and content matching {cta.content.pattern!r}"
    case_note.set(action=cta.action, expectation=expectation)
    ctx = _ctx(browser_name, base_url, cta.action, expectation)
    _load_home(page, base_url, ctx)

    link = _cta_link(page, cta, ctx)
    _reveal_hero_slide(page, link, ctx)
    link.click()
    page.wait_for_load_state("domcontentloaded")

    current = page.url
    ctx_after = _ctx(browser_name, current, cta.action, expectation)
    expected_url = urljoin(base_url, cta.expect_path.lstrip("/"))
    assert cta.expect_path.rstrip("/") in current.rstrip("/"), (
        f"[{ctx_after}] Expected URL to include path {cta.expect_path!r} "
        f"(resolved {expected_url!r})"
    )
    _assert_not_error_page(page, ctx_after)
    _assert_heading(page, cta.heading, ctx_after)
    expect(
        page.get_by_text(cta.content).first,
        f"[{ctx_after}] Expected destination content matching {cta.content.pattern!r}",
    ).to_be_visible()
    if cta.contact_form:
        _assert_contact_form_usable(page, ctx_after)


def test_home_scroll_reaches_below_the_fold(
    page: Page,
    base_url: str,
    browser_name: str,
    case_note: CaseNote,
) -> None:
    """Scroll the long home page until below-the-fold sections are actually in view."""
    action = "scroll home page through below-the-fold sections"
    expectation = (
        f"heading {READY_TO_START!r} enters the viewport after {WHY_CHOOSE.pattern!r} is reached"
    )
    case_note.set(action=action, expectation=expectation)
    ctx = _ctx(browser_name, base_url, action, expectation)
    page.set_viewport_size(VIEWPORT)
    _load_home(page, base_url, ctx)

    height = VIEWPORT["height"]
    hero = _visible_heading(page, HERO_HEADING, ctx)
    why = _visible_heading(page, WHY_CHOOSE, ctx)
    ready = _visible_heading(page, READY_TO_START, ctx)

    expect(hero, f"[{ctx}] Expected the home hero to start in the viewport").to_be_in_viewport()
    why_top = _box_top(why, ctx)
    ready_top = _box_top(ready, ctx)
    assert why_top >= height, (
        f"[{ctx}] Expected 'Why Choose Kubozoa?' to start below the fold, top={why_top}"
    )
    assert ready_top > why_top, (
        f"[{ctx}] Expected 'Ready to get started?' below 'Why Choose Kubozoa?', "
        f"ready_top={ready_top} why_top={why_top}"
    )

    saw_why = False
    ready_in_view = False
    for _step in range(MAX_SCROLL_STEPS):
        if _intersects_viewport(why, height):
            saw_why = True
        if saw_why and _intersects_viewport(ready, height):
            ready_in_view = True
            break
        _scroll_down(page, SCROLL_STEP_PX)

    end_y = int(page.evaluate("() => window.scrollY"))
    ctx_after = _ctx(browser_name, page.url, action, expectation)
    assert saw_why, (
        f"[{ctx_after}] Scrolling never brought 'Why Choose Kubozoa?' into view (scrollY={end_y})"
    )
    assert ready_in_view, (
        f"[{ctx_after}] Scrolling never brought {READY_TO_START!r} into view (scrollY={end_y})"
    )
    expect(
        ready,
        f"[{ctx_after}] Expected {READY_TO_START!r} to be in the viewport after scrolling",
    ).to_be_in_viewport()
    assert end_y > 0, f"[{ctx_after}] Expected the document to scroll, scrollY={end_y}"
