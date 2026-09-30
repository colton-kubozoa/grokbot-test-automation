# Feature: CI checks the application, not the live site

## Goal

The required CI check reports whether this repository builds and its own code behaves. The browser suite still runs and still writes `results/latest.json`, in a job that is not required for merge.

A full `pytest` run visits [https://www.kubozoa.com/](https://www.kubozoa.com/) in Chromium, Firefox, and WebKit. Those 26 cases (78 records) observe a public site this repository does not build or deploy. A miss there means the site changed, a page was slow, or the network failed. The result writer, the dashboard, and the rest of this code can still be fine.

Today the `test-playwright` job in `.github/workflows/ci.yml` runs `pytest` with no selection after installing browsers. That single job is what CI treats as the test stage, so a live-site failure fails the pipeline.

## What the required check runs

On pull requests and pushes to `main`, the required jobs stay:

- dependency audit
- lint and typecheck
- pytest for tests that do not launch a browser or call the network (`tests/test_result_store.py`)

Those unit tests cover the result writer. A failure there means this code is wrong, and the required check stays red.

The required test step selects those tests explicitly (`pytest tests/test_result_store.py`). It does not install Playwright browsers.

## What the browser job does

A separate job runs the Playwright cases in `tests/` against `BASE_URL` (default `https://www.kubozoa.com/`) on Chromium, Firefox, and WebKit. When the run finishes, the job uploads `results/latest.json`, including when cases fail, so the dashboard can still read which case and which browser failed.

That job is not a required status check for merging. It may run on a schedule or be started by hand. A red result is the site report. It does not block a change that only touched application code.

A local `pytest` and the image entrypoint remain a full suite run, browser cases included. The split is in CI, where "this build is healthy" and "the live site matched the cases" are two signals.

## Out of scope

- Changing the visitor cases, the result schema, or the dashboard
- Removing the browser suite from the repository
- Changing the public Kubozoa site
- Making the browser job a required merge check

## Success

A pull request that breaks `tests/test_result_store.py` fails the required check. A pull request that leaves that file and the lint jobs passing succeeds even when the live site would fail a browser case. The browser job can still be run, and its artifact is `results/latest.json`.
