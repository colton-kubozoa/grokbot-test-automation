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

When the session finishes, case outcomes are in `results/latest.json`.
What each case covers is listed in `tests/TEST_CASES.md`. Details of the
results file are below.

## Stored results

`pytest` writes one record per case per browser to `results/latest.json`.
That file is overwritten at the start of each session. It is the primary path
for a local demo, the dashboard, and the CI artifact. Each suite
invocation also keeps a copy at `results/runs/<run-id>.json`.

Live output under `results/` is gitignored. `results/sample.json` is the
committed example of the file shape. It is not a live run.

The file is a JSON object, schema version 1, with:

- `schema_version`
- `run` — `id`, `started_at`, `finished_at`, and `status`
  (`in_progress`, `finished`, or `interrupted`)
- `target` — site root under test (`BASE_URL`)
- `records` — one object per case per browser

The module docstring in `tests/result_store.py` is the in-repo source of truth
for the full field list. These paths are written at the pytest root (the
repository when you run `pytest` locally). `docker run --rm` writes them inside
the container.

## Dashboard

A static page reads one schema version 1 results file and lists every case ×
browser with pass or fail. A failed row expands to the browser, URL, action,
expectation, and failure message. The page does not write JSON, re-run tests,
or launch browsers.

Opening `dashboard/index.html` with `file://` cannot fetch local JSON. From
the repository root:

```bash
python dashboard/serve.py
```

Then open [http://127.0.0.1:8765/dashboard/](http://127.0.0.1:8765/dashboard/).

The default file is `results/latest.json`. If that file is missing (HTTP 404
only), the page falls back to `results/sample.json` and says so. `?file=latest`,
`?file=sample`, or `?file=results/sample.json` selects a file. An invalid or
empty `latest.json` is not replaced by the sample. A valid file with zero
records shows an empty state, not a passing run.

`dashboard/fixtures/` holds empty, invalid, and zero-record files for the
page's preview links. A missing-file preview requests a path that is not in
the repo. `tests/test_dashboard_server.py` checks that the local server serves
the dashboard and results JSON and refuses other repository files.

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
- `tests/result_store.py` — writes suite outcomes to `results/latest.json`; its module docstring is the schema source of truth
- `tests/test_result_store.py` — unit tests for the result writer (no browser and no network)
- `tests/TEST_CASES.md` — inventory of suite cases and what pass or fail means
- `results/` — `sample.json` is a committed example of the results file. Live output (`latest.json` and `runs/<run-id>.json`) is gitignored
- `dashboard/` — static test-results page and `serve.py`, which serves it on localhost
- `tests/test_dashboard_server.py` — checks the dashboard server allowlist
- `requirements.txt` — pinned `pytest` and `playwright`
- `pyproject.toml` — pytest discovery plus ruff/mypy config for CI lint/typecheck
- `Dockerfile` — container image that installs browsers and runs `pytest`
