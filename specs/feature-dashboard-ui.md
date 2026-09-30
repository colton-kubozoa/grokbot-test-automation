# Feature: Test results dashboard UI

## Goal

A simple front-end dashboard lists every browser test case and shows whether that case passed or failed. The dashboard reads a JSON file of stored results. It does not launch browsers, run `pytest`, or depend on a terminal session.

The JSON file is produced by the stored-results feature. This feature is the UI that reads that file.

## What the dashboard shows

The dashboard opens the JSON file and presents one row (or card) per test case:

| Shown item | Source in the JSON record |
| --- | --- |
| Case | Case id |
| Description | Description of what the visitor did and what the case expected |
| Result | Status: `pass` or `fail` |
| Browser | `chromium`, `firefox`, or `webkit` |

A case that ran in more than one browser appears once per browser, because each browser outcome is its own record. Pass and fail must be visually distinct so a failure is obvious next to the cases that passed.

The list must include every record in the file. Filtering or hiding a case is optional and must never be the only way to see a failure.

## How it reads the file

The dashboard loads one JSON file of result records. It does not compute pass or fail itself. Status, description, and case id come from the file.

Each record supplies:

| Field | Use in the UI |
| --- | --- |
| Case id | Stable label for the case |
| Description | Text shown beside the case |
| Status | `pass` or `fail` |
| Browser | Which browser that outcome belongs to |
| Run | Which suite run the record came from |
| Target | Site root that was under test |
| Context | URL, action, and expectation; on failure, the assertion message |

A failed row must be openable so the browser, URL, action, expectation, and failure message are visible without leaving the dashboard.

If the file is missing, empty, or not valid JSON, the dashboard shows that state instead of an empty success list.

## Out of scope

- Writing or updating the JSON file
- Re-running tests from the dashboard
- Changing the public Kubozoa site
- Editing case descriptions in the UI
- Login, accounts, or charts beyond pass versus fail
