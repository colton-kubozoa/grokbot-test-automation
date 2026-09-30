# Browser suite test cases

Each case runs once per browser: `chromium`, `firefox`, and `webkit`. A full run stores **78 records** (26 cases × 3 browsers) in `results/latest.json`. The stored `case_id` is the pytest node id. A case with no parameter looks like `tests/test_home_smoke.py::test_home_page_loads_with_key_content[chromium]`. A parametrized case looks like `tests/test_primary_nav.py::test_primary_nav_destination[firefox-who-we-are]` (`<browser>-<parameter id>`).

A **pass** means every assertion in that case held for that browser. A **fail** means an assertion in that case failed. The assertion message is stored on that record. The other browsers are separate records.

Outcomes are written by `tests/result_store.py` (schema version 1). `results/sample.json` is a committed example, not a live run. `tests/test_result_store.py` checks the writer and does not visit the site, so those tests are not result records.

These cases do not cover KuboLib (the block is hidden and `/kubosuite/kubolib/` is not a visitor destination), third-party social profiles, or hash-only footer address and email links. No case submits the contact form or enters personal data.

## Home smoke

`tests/test_home_smoke.py::test_home_page_loads_with_key_content[<browser>]`

The visitor opens the home page.

- **Pass:** the response is HTTP success, the title and logo show Kubozoa, the primary nav shows What we do, Who we are, Join us, and Get in touch, and the hero heading "Cloud Native. Streamlined. Simplified" is visible.
- **Fail:** the navigation response is missing, the HTTP status is not success, or any of those elements is missing.

## Primary navigation

`tests/test_primary_nav.py::test_primary_nav_destination[<browser>-<parameter id>]`

The visitor starts on the home page and follows one in-site link. Every case below fails when the home page does not load, the primary nav is missing, the click does not reach the expected path, the destination looks like an error page (title contains "404" or "not found"), or the expected heading is not visible.

| Parameter id | What the visitor does | Pass |
| --- | --- | --- |
| `kubosuite-via-what-we-do` | Hover What we do, then click KuboSuite | Path includes `/kubosuite/` and a KuboSuite heading is visible |
| `services-via-what-we-do` | Hover What we do, then click Services | Path includes `/services/` and the Services heading is visible |
| `who-we-are` | Click primary nav Who we are | Path includes `/who-we-are/` and the Who we are heading is visible |
| `join-us` | Click primary nav Join us | Path includes `/join-us/` and the Join us heading is visible |
| `get-in-touch` | Click primary nav Get in touch | Path includes `/get-in-touch/` and the Get in touch heading is visible. The contact form is not filled in or submitted |
| `kubosuite-products-overview` | Click See all KuboSuite Products | Path includes `/kubosuite/` and a KuboSuite heading is visible |

## Home CTAs

`tests/test_cta_scroll.py::test_home_cta_reaches_expected_content[<browser>-<parameter id>]`

The visitor starts on the home page and follows one call to action. Hero CTAs are brought onto the active slide before the click. A case fails when the home page does not load, the CTA link is missing, the URL does not include the expected path, the destination looks like an error page, the expected heading is missing, or the expected content text is missing.

| Parameter id | What the visitor does | Pass |
| --- | --- | --- |
| `more-about-us` | Show the hero slide, then click More about us | `/who-we-are/` shows the Who we are heading and text matching "Kubozoans" |
| `learn-more` | Show the hero slide, then click Learn more | `/kubosuite/` shows a KuboSuite heading and text matching "complementary products" |
| `read-more` | Show the hero slide, then click Read more | `/services/` shows the Services heading and text matching "implementation services" |
| `view-open-positions` | Show the hero slide, then click View open positions | `/join-us/` shows the Join us heading and text matching "hiring process" |
| `see-all-kubosuite-products` | Click See all KuboSuite Products | `/kubosuite/` shows a KuboSuite heading and text matching "complementary products" |
| `get-in-touch` | Click Get In touch | `/get-in-touch/` shows the Get in touch heading and text matching "Get in touch with us". The contact form and its name, email, message, and submit controls are visible and enabled, and the fields are empty. Nothing is typed and the form is not submitted. **Fail** also covers a missing, disabled, or pre-filled field |

## Home scroll

`tests/test_cta_scroll.py::test_home_scroll_reaches_below_the_fold[<browser>]`

The visitor opens the home page at a 1280×720 viewport and scrolls down in steps.

- **Pass:** the hero starts in the viewport, "Why Choose Kubozoa?" starts below the fold and above "Ready to get started?", scrolling brings "Why Choose Kubozoa?" into view and then brings "Ready to get started?" into the viewport, and the document scroll offset is greater than zero.
- **Fail:** a heading is missing, the sections are in the wrong order, or scrolling never brings them into view.

## KuboSuite products

`tests/test_kubosuite_products.py::test_kubosuite_product_entry[<browser>-<parameter id>]`

The visitor opens the home page, clicks See all KuboSuite Products, then opens one product from the overview. A case fails when the home page or overview does not load, the overview is an error page, the product link is missing, the product path is wrong, the product page looks like an error page, or the expected heading or content is missing.

| Parameter id | Destination | Pass |
| --- | --- | --- |
| `kubodevelop` | `/kubosuite/kubodevelop/` | Heading KuboDevelop and text matching "non-functional aspects of a microservice" |
| `kubosecure` | `/kubosuite/kubosecure/` | Heading KuboSecure and text matching "Shift Security Left" |
| `kubooperate` | `/kubosuite/kubooperate/` | Heading KuboOperate and text matching "move their workloads to the cloud" |

## Footer destinations

`tests/test_footer_destinations.py::test_footer_destination_from_home[<browser>-<parameter id>]`

The visitor opens the home page and follows one same-site link in the footer. A case fails when the home page does not load, the footer or the named link is missing, the path or host is wrong, the destination looks like an error page, or the expected heading or content is missing.

| Parameter id | Destination | Pass |
| --- | --- | --- |
| `kubodevelop` | `/kubosuite/kubodevelop/` | Heading KuboDevelop and text matching "non-functional aspects of a microservice" |
| `kubosecure` | `/kubosuite/kubosecure/` | Heading KuboSecure and text matching "Shift Security Left" |
| `kubooperate` | `/kubosuite/kubooperate/` | Heading KuboOperate and text matching "move their workloads to the cloud" |
| `see-all-products` | `/kubosuite/` | Heading KuboSuite and text matching "complementary products" |
| `what-we-do` | `/kubosuite` | Heading KuboSuite and text matching "complementary products" |
| `who-we-are` | `/who-we-are/` | Heading Who we are and text matching "Kubozoans" |
| `join-us` | `/join-us/` | Heading Join us and text matching "hiring process" |
| `get-in-touch` | `/get-in-touch/` | Heading Get in touch and text matching "Get in touch with us". The form is not submitted |
| `privacy-policy` | `/privacy-policy/` | Heading Privacy Policy and text matching "Our website address is" |
