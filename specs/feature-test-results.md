# Feature: Stored browser test results

## Goal

Every browser test case in this suite must leave a durable result that a front-end dashboard can read later. The dashboard is a later consumer. It is not part of the test run, and it must not depend on a terminal session, a pytest process, or a human copying output out of logs.

A result is useful only when it survives the run that produced it. After `pytest` exits, a separate front end must still be able to list the cases, read each description, and show which cases passed and which failed, including which browser that outcome belonged to.

## What must be stored

Each execution of a test case in one browser is one stored record in a JSON file. A full run therefore stores one record per case per browser (Chromium, Firefox, and WebKit) in that file.

| Field | Required content |
| --- | --- |
| Run | Identity of the suite run, with when it finished |
| Browser | `chromium`, `firefox`, or `webkit` |
| Case id | Stable id for the case (pytest node id is acceptable) |
| Description | What the visitor did and what the case expected |
| Status | `pass` or `fail` |
| Target | Site root under test (`BASE_URL`, default `https://www.kubozoa.com/`) |
| Context | URL, action, and expectation. On failure, the assertion message that explains what broke |

The JSON file is the source the dashboard reads. A log line that only appears in CI output does not meet this need, because the dashboard cannot query it after the job ends.

## How a dashboard uses the store

The dashboard reads the JSON file. It does not re-run the browsers. From those records it must be able to:

1. List every test case with its description.
2. Show pass versus fail for each case, separately for each browser.
3. Open a failed record and see the browser, URL, action, expectation, and failure message.
4. Compare a later run with an earlier one without losing the earlier result.

The dashboard UI itself is out of scope for this feature. This feature is the JSON file of stored records that UI will read.

## Test cases

A full list of test cases and what passes or fails needs to be documented in a markdown file.

## Out of scope

- Building the front-end dashboard
- Changing the public Kubozoa site
- Submitting the contact form or storing personal data from it
- Treating KuboLib, third-party social links, or hash-only footer links as visitor destinations
