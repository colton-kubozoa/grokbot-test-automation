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
products overview.

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

- `tests/` — pytest suite and shared Playwright fixtures (`test_home_smoke.py`, `test_primary_nav.py`)
- `requirements.txt` — pinned `pytest` and `playwright`
- `pyproject.toml` — pytest discovery plus ruff/mypy config for CI lint/typecheck
- `Dockerfile` — container image that installs browsers and runs `pytest`
