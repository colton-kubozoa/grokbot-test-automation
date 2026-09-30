"""Write browser-suite outcomes to durable JSON.

Primary path (overwritten on every suite run): ``results/latest.json``
History (one file per invocation, kept so an earlier run is not lost):
``results/runs/<run-id>.json``
Committed example (not a live run): ``results/sample.json``

The dashboard (Issue #12) loads one JSON object and iterates ``records``.
The file is not a bare array. CI (Issue #13) uploads ``results/latest.json``.

Schema version 1
----------------
Document:

- ``schema_version`` (int): ``1``
- ``run.id`` (str): identity of this suite invocation
- ``run.started_at`` (str): UTC timestamp when the run started (ISO-8601, ``Z``)
- ``run.finished_at`` (str | null): UTC timestamp when pytest finished the
  session; null while ``run.status`` is ``in_progress``
- ``run.status`` (str): ``in_progress`` | ``finished`` | ``interrupted``
  - ``in_progress``: pytest is still running, or the process was killed
    before session finish. Records already flushed are kept.
  - ``finished``: the session completed (exit 0, tests failed, or no tests).
    Individual records may still be ``fail``.
  - ``interrupted``: the session did not complete (keyboard interrupt or
    internal error). Records are only the cases that finished.
- ``target`` (str): site root (``BASE_URL``, default ``https://www.kubozoa.com/``)
- ``records`` (array): one object per case per browser

Record:

- ``run.id`` (str): same as the document run id
- ``run.finished_at`` (str | null): same as the document ``run.finished_at``
- ``recorded_at`` (str): UTC timestamp when this case outcome was stored
- ``browser`` (str): ``chromium``, ``firefox``, ``webkit``, or ``unknown``
  when the browser fixture did not yield a name
- ``case_id`` (str): pytest node id
- ``description`` (str): visitor action and expectation,
  ``"<action>; expected: <expectation>"``
- ``status`` (str): ``pass`` or ``fail``
- ``target`` (str): same as the document target
- ``context.url`` (str): page URL at the end of the test, else the target
- ``context.action`` (str): what the visitor did
- ``context.expectation`` (str): what the case expected
- ``context.assertion_message`` (str | null): null on pass; on fail, the
  assertion message (no traceback)

A new run replaces ``results/latest.json`` immediately, before tests execute,
so a killed process cannot leave a previous full-success file in place.
Cases already finished are flushed after each one.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, TypedDict

import pytest

_LOG = logging.getLogger("tests.result_store")

SCHEMA_VERSION = 1
DEFAULT_BASE_URL = "https://www.kubozoa.com/"
LATEST_FILENAME = "latest.json"
RUNS_DIRNAME = "runs"
_RESULT_FIXTURES = frozenset({"page", "browser_name", "case_note"})
_ALLOWED_BROWSERS = frozenset({"chromium", "firefox", "webkit", "unknown"})
_FINISHED_EXIT_CODES = frozenset({0, 1, 5})
_MAX_ASSERTION_CHARS = 4000


class RunIdentity(TypedDict):
    id: str
    finished_at: str | None


class ResultContext(TypedDict):
    url: str
    action: str
    expectation: str
    assertion_message: str | None


class ResultRecord(TypedDict):
    run: RunIdentity
    recorded_at: str
    browser: str
    case_id: str
    description: str
    status: str
    target: str
    context: ResultContext


class RunSummary(TypedDict):
    id: str
    started_at: str
    finished_at: str | None
    status: str


class ResultDocument(TypedDict):
    schema_version: int
    run: RunSummary
    target: str
    records: list[ResultRecord]


def resolve_target(raw: str | None = None) -> str:
    """Site root with a trailing slash. Defaults to ``BASE_URL`` or kubozoa.com."""
    if raw is None:
        raw = os.environ.get("BASE_URL", DEFAULT_BASE_URL)
    value = raw.strip() or DEFAULT_BASE_URL
    return value if value.endswith("/") else f"{value}/"


def _iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _run_id(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    stamp = moment.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:12]}"


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def build_record(
    *,
    run_id: str,
    recorded_at: str,
    browser: str,
    case_id: str,
    description: str,
    status: str,
    target: str,
    url: str,
    action: str,
    expectation: str,
    assertion_message: str | None,
) -> ResultRecord:
    """Build one case×browser record. Raises ``ValueError`` when the shape is wrong."""
    if status not in ("pass", "fail"):
        raise ValueError(f"status must be 'pass' or 'fail', got {status!r}")
    if browser not in _ALLOWED_BROWSERS:
        raise ValueError(f"browser must be one of {sorted(_ALLOWED_BROWSERS)}, got {browser!r}")
    if status == "pass":
        if assertion_message is not None:
            raise ValueError("pass records must not include an assertion message")
        failure: str | None = None
    else:
        failure = assertion_message.strip() if isinstance(assertion_message, str) else ""
        if not failure:
            failure = "failed"
    return {
        "run": {"id": _require_text(run_id, "run.id"), "finished_at": None},
        "recorded_at": _require_text(recorded_at, "recorded_at"),
        "browser": browser,
        "case_id": _require_text(case_id, "case_id"),
        "description": _require_text(description, "description"),
        "status": status,
        "target": _require_text(target, "target"),
        "context": {
            "url": _require_text(url, "context.url"),
            "action": _require_text(action, "context.action"),
            "expectation": _require_text(expectation, "context.expectation"),
            "assertion_message": failure,
        },
    }


def validate_document(document: object) -> ResultDocument:
    """Raise ``ValueError`` when ``document`` does not match schema version 1."""
    if not isinstance(document, dict):
        raise ValueError("result document must be a JSON object")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    run = document.get("run")
    if not isinstance(run, dict):
        raise ValueError("run must be an object")
    run_id = _require_text(run.get("id"), "run.id")
    started_at = _require_text(run.get("started_at"), "run.started_at")
    status = run.get("status")
    if status not in ("in_progress", "finished", "interrupted"):
        raise ValueError("run.status must be in_progress, finished, or interrupted")
    finished_at = run.get("finished_at")
    if status == "in_progress":
        if finished_at is not None:
            raise ValueError("in_progress runs must have run.finished_at null")
    elif not isinstance(finished_at, str) or not finished_at.strip():
        raise ValueError("finished runs must include run.finished_at")
    target = _require_text(document.get("target"), "target")
    records = document.get("records")
    if not isinstance(records, list):
        raise ValueError("records must be an array")
    validated: list[ResultRecord] = []
    for index, record in enumerate(records):
        validated.append(_validate_record(record, index, run_id, finished_at, target))
    return {
        "schema_version": SCHEMA_VERSION,
        "run": {
            "id": run_id,
            "started_at": started_at,
            "finished_at": finished_at if isinstance(finished_at, str) else None,
            "status": status,
        },
        "target": target,
        "records": validated,
    }


def _validate_record(
    record: object,
    index: int,
    run_id: str,
    finished_at: object,
    target: str,
) -> ResultRecord:
    label = f"records[{index}]"
    if not isinstance(record, dict):
        raise ValueError(f"{label} must be an object")
    run = record.get("run")
    if not isinstance(run, dict):
        raise ValueError(f"{label}.run must be an object")
    if run.get("id") != run_id:
        raise ValueError(f"{label}.run.id must match the document run id")
    if run.get("finished_at") != finished_at:
        raise ValueError(f"{label}.run.finished_at must match the document run")
    status = record.get("status")
    if not isinstance(status, str) or status not in ("pass", "fail"):
        raise ValueError(f"{label}.status must be pass or fail")
    browser = record.get("browser")
    if not isinstance(browser, str) or browser not in _ALLOWED_BROWSERS:
        raise ValueError(f"{label}.browser is not a known browser")
    context = record.get("context")
    if not isinstance(context, dict):
        raise ValueError(f"{label}.context must be an object")
    message = context.get("assertion_message")
    if status == "pass" and message is not None:
        raise ValueError(f"{label} pass records must have assertion_message null")
    if status == "fail" and (not isinstance(message, str) or not message.strip()):
        raise ValueError(f"{label} fail records must include assertion_message")
    if record.get("target") != target:
        raise ValueError(f"{label}.target must match the document target")
    return {
        "run": {"id": run_id, "finished_at": finished_at if isinstance(finished_at, str) else None},
        "recorded_at": _require_text(record.get("recorded_at"), f"{label}.recorded_at"),
        "browser": browser,
        "case_id": _require_text(record.get("case_id"), f"{label}.case_id"),
        "description": _require_text(record.get("description"), f"{label}.description"),
        "status": status,
        "target": target,
        "context": {
            "url": _require_text(context.get("url"), f"{label}.context.url"),
            "action": _require_text(context.get("action"), f"{label}.context.action"),
            "expectation": _require_text(
                context.get("expectation"), f"{label}.context.expectation"
            ),
            "assertion_message": message if isinstance(message, str) else None,
        },
    }


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


class ResultStore:
    """In-memory run that flushes ``latest.json`` and a history file."""

    def __init__(self, directory: Path, target: str) -> None:
        self.directory = directory
        self.latest_path = directory / LATEST_FILENAME
        self.runs_dir = directory / RUNS_DIRNAME
        self.target = target
        self.run_id = ""
        self.started_at = ""
        self.finished_at: str | None = None
        self.status = "in_progress"
        self.records: dict[str, ResultRecord] = {}

    def start(self, *, now: datetime | None = None) -> None:
        moment = now or datetime.now(UTC)
        self.run_id = _run_id(moment)
        self.started_at = _iso(moment)
        self.finished_at = None
        self.status = "in_progress"
        self.records = {}
        self.flush()

    def add(self, record: ResultRecord) -> None:
        if record["run"]["id"] != self.run_id:
            raise ValueError("record run id does not match this store")
        if record["target"] != self.target:
            raise ValueError("record target does not match this store")
        key = f"{record['browser']}\n{record['case_id']}"
        self.records[key] = record
        self.flush()

    def finish(self, *, exitstatus: int = 0, now: datetime | None = None) -> None:
        self.finished_at = _iso(now or datetime.now(UTC))
        self.status = "finished" if exitstatus in _FINISHED_EXIT_CODES else "interrupted"
        for record in self.records.values():
            record["run"]["finished_at"] = self.finished_at
        self.flush()

    def document(self) -> ResultDocument:
        return {
            "schema_version": SCHEMA_VERSION,
            "run": {
                "id": self.run_id,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "status": self.status,
            },
            "target": self.target,
            "records": list(self.records.values()),
        }

    def flush(self) -> None:
        if not self.run_id:
            raise RuntimeError("result store has not been started")
        text = json.dumps(self.document(), indent=2, ensure_ascii=False) + "\n"
        validate_document(json.loads(text))
        _atomic_write(self.runs_dir / f"{self.run_id}.json", text)
        _atomic_write(self.latest_path, text)
        _LOG.info(
            "Wrote %d result record(s) to %s (run %s, %s)",
            len(self.records),
            self.latest_path,
            self.run_id,
            self.status,
        )


class CaseNote:
    """Visitor action and expectation captured by a browser test."""

    def __init__(self) -> None:
        self.action = ""
        self.expectation = ""
        self.url: str | None = None

    def set(self, *, action: str, expectation: str, url: str | None = None) -> None:
        self.action = action
        self.expectation = expectation
        if url is not None:
            self.url = url


CASE_NOTE_KEY = pytest.StashKey[CaseNote]()
_STORE: ResultStore | None = None


@pytest.fixture
def case_note(request: pytest.FixtureRequest) -> CaseNote:
    """Record the visitor action and expectation for ``results/latest.json``."""
    note = CaseNote()
    request.node.stash[CASE_NOTE_KEY] = note
    return note


def _is_result_case(item: pytest.Item) -> bool:
    names = getattr(item, "fixturenames", ())
    return any(name in names for name in _RESULT_FIXTURES)


def _browser_from_item(item: pytest.Item) -> str:
    funcargs = getattr(item, "funcargs", None)
    if isinstance(funcargs, dict):
        value = funcargs.get("browser_name")
        if isinstance(value, str) and value.strip():
            return value.strip()
    callspec = getattr(item, "callspec", None)
    params = getattr(callspec, "params", None) if callspec is not None else None
    if isinstance(params, dict):
        value = params.get("browser_name")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def _url_from_item(item: pytest.Item, note: CaseNote | None, target: str) -> str:
    funcargs = getattr(item, "funcargs", None)
    page = funcargs.get("page") if isinstance(funcargs, dict) else None
    if page is not None:
        try:
            url = getattr(page, "url", None)
        except Exception as exc:
            _LOG.debug("Could not read page URL for %s: %s", item.nodeid, exc)
            url = None
        if isinstance(url, str) and url.strip() and url != "about:blank":
            return url
    if note is not None and note.url:
        return note.url
    return target


def _note_from_item(item: pytest.Item) -> CaseNote | None:
    stash = getattr(item, "stash", None)
    getter = getattr(stash, "get", None)
    if getter is None:
        return None
    note = getter(CASE_NOTE_KEY, None)
    return note if isinstance(note, CaseNote) else None


def _describe(item: pytest.Item, note: CaseNote | None) -> tuple[str, str, str]:
    action = note.action.strip() if note is not None else ""
    expectation = note.expectation.strip() if note is not None else ""
    if not action or not expectation:
        doc = ""
        function = getattr(item, "obj", None)
        if function is not None:
            doc = (getattr(function, "__doc__", None) or "").strip()
        first = doc.splitlines()[0].strip() if doc else ""
        fallback = first or item.nodeid
        if not action:
            action = fallback
        if not expectation:
            expectation = fallback
    return f"{action}; expected: {expectation}", action, expectation


def _clip(text: str) -> str:
    stripped = text.strip()
    if len(stripped) <= _MAX_ASSERTION_CHARS:
        return stripped
    return stripped[:_MAX_ASSERTION_CHARS] + "…"


def failure_message(report: pytest.TestReport, call: pytest.CallInfo[None] | None = None) -> str:
    """Assertion text for a failed report, without a traceback."""
    if call is not None and call.excinfo is not None:
        text = str(call.excinfo.value).strip()
        if text:
            return _clip(text)
    longrepr = report.longrepr
    crash = getattr(longrepr, "reprcrash", None)
    message = getattr(crash, "message", None) if crash is not None else None
    if isinstance(message, str) and message.strip():
        return _clip(message)
    if longrepr is not None:
        text = str(longrepr).strip()
        if text:
            return _clip(text)
    return "failed"


def _report_status(report: pytest.TestReport) -> str | None:
    if report.skipped:
        return None
    if report.passed:
        return "pass"
    if report.failed:
        return "fail"
    return None


def consume_report(
    store: ResultStore,
    item: pytest.Item,
    report: pytest.TestReport,
    *,
    failure_text: str | None = None,
) -> None:
    """Record one setup/call/teardown report. Non-browser tests are ignored."""
    if not _is_result_case(item):
        return
    status = _report_status(report)
    if status is None or report.when not in ("setup", "call", "teardown"):
        return
    if report.when in ("setup", "teardown") and status == "pass":
        return

    browser = _browser_from_item(item)
    case_id = item.nodeid
    key = f"{browser}\n{case_id}"
    existing = store.records.get(key)
    message = failure_text if status == "fail" else None
    if status == "fail" and not message:
        message = failure_message(report)

    if report.when == "teardown" and existing is not None and status == "fail":
        previous = existing["context"]["assertion_message"]
        if existing["status"] == "pass" or not previous:
            existing["context"]["assertion_message"] = message or "failed"
        elif message:
            existing["context"]["assertion_message"] = _clip(f"{previous}\n{message}")
        existing["status"] = "fail"
        existing["recorded_at"] = _iso(datetime.now(UTC))
        store.flush()
        return

    if report.when == "setup" and existing is not None:
        return

    note = _note_from_item(item)
    description, action, expectation = _describe(item, note)
    record = build_record(
        run_id=store.run_id,
        recorded_at=_iso(datetime.now(UTC)),
        browser=browser,
        case_id=case_id,
        description=description,
        status=status,
        target=store.target,
        url=_url_from_item(item, note, store.target),
        action=action,
        expectation=expectation,
        assertion_message=message,
    )
    store.add(record)


def pytest_sessionstart(session: pytest.Session) -> None:
    global _STORE
    if getattr(session.config.option, "collectonly", False):
        _STORE = None
        return
    store = ResultStore(Path(session.config.rootpath) / "results", resolve_target())
    store.start()
    _STORE = store


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    del session
    if _STORE is None:
        return
    _STORE.finish(exitstatus=int(exitstatus))


class _HookResult(Protocol):
    def get_result(self) -> pytest.TestReport: ...


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo[None],
) -> Generator[None, _HookResult, None]:
    outcome = yield
    if _STORE is None:
        return
    report = outcome.get_result()
    text = failure_message(report, call) if report.failed else None
    consume_report(_STORE, item, report, failure_text=text)
