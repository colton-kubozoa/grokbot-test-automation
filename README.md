# grokbot-test-automation

Playwright + pytest proof-of-concept suite against the public Kubozoa site
([https://www.kubozoa.com/](https://www.kubozoa.com/)).

## Local setup

Requires **Python 3.12+**.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
playwright install --with-deps chromium firefox webkit
```

On systems where OS deps are already present (or inside the Playwright Docker image),
`playwright install chromium firefox webkit` is enough.

## Run the suite

```bash
pytest
```

Override the target site (default `https://www.kubozoa.com/`):

```bash
BASE_URL=https://www.kubozoa.com/ pytest
```

`pytest` runs the home-page smoke and primary-nav destination flows once per
browser (Chromium, Firefox, and WebKit). Primary-nav cases cover KuboSuite™ and
Services (via What we do), Who we are, Join us, Get in touch, and the KuboSuite™
products overview. It also covers home CTA clicks (More about us, Learn more,
Read more, View open positions, See all KuboSuite™ Products, and Get In touch)
and a scroll-through of below-the-fold home sections, on the same three
browsers. The Get In touch path asserts the contact form is open and usable.
No personal data is entered, and the form is not submitted. The same run opens
the visitor-visible KuboSuite™ product entries from the products overview
(KuboDevelop™, KuboSecure™, and KuboOperate™) and follows same-site home footer
destinations, including Privacy Policy, on Chromium, Firefox, and WebKit.
KuboLib™ is omitted because that block is hidden on the live site and
`/kubosuite/kubolib/` returns not-found, so it is not a destination a visitor
can open. Footer coverage is in-site only: third-party social profiles and
hash-only address and email links are not followed.

## Docker

The `Dockerfile` uses the official Playwright Python image, installs pinned deps and
browsers, and defaults to `pytest`.

```bash
docker build -t grokbot-test-automation .
docker run --rm grokbot-test-automation
```

Override the target site:

```bash
docker run --rm -e BASE_URL=https://www.kubozoa.com/ grokbot-test-automation
```

## Layout

- `tests/` — pytest suite and shared Playwright fixtures (`test_home_smoke.py`, `test_primary_nav.py`, `test_cta_scroll.py`, `test_kubosuite_products.py`, `test_footer_destinations.py`)
- `requirements.txt` — pinned `pytest` and `playwright`
- `pyproject.toml` — pytest discovery plus ruff/mypy config for CI lint/typecheck
- `Dockerfile` — container image that installs browsers and runs `pytest`
