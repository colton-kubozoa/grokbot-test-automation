"""Unit tests for the durable JSON result store. No network and no browsers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from result_store import (
    CASE_NOTE_KEY,
    DEFAULT_BASE_URL,
    CaseNote,
    ResultDocument,
    ResultStore,
    build_record,
    consume_report,
    failure_message,
    resolve_target,
    validate_document,
)

TARGET = "https://www.kubozoa.com/"
NODE_ID = "tests/test_home_smoke.py::test_home_page_loads_with_key_content[chromium]"


class _Stash:
    def __init__(self) -> None:
        self._data: dict[object, object] = {}

    def get(self, key: object, default: object = None) -> object:
        return self._data.get(key, default)

    def __setitem__(self, key: object, value: object) -> None:
        self._data[key] = value


class _Item:
    def __init__(self, browser: str, nodeid: str = NODE_ID, url: str = TARGET) -> None:
        self.nodeid = nodeid
        self.fixturenames = ["page", "base_url", "browser_name", "case_note"]
        self.funcargs: dict[str, object] = {
            "browser_name": browser,
            "base_url": TARGET,
            "page": SimpleNamespace(url=url),
        }
        self.stash = _Stash()
        self.obj: object | None = None

    def note(self, action: str, expectation: str, url: str | None = None) -> None:
        case = CaseNote()
        case.set(action=action, expectation=expectation, url=url)
        self.stash[CASE_NOTE_KEY] = case


def _as_item(item: _Item) -> pytest.Item:
    return cast(pytest.Item, item)


def _report(when: str, outcome: str, message: str | None = None) -> pytest.TestReport:
    longrepr = None
    if message is not None:
        longrepr = SimpleNamespace(reprcrash=SimpleNamespace(message=message))
    return cast(
        pytest.TestReport,
        SimpleNamespace(
            when=when,
            passed=outcome == "pass",
            failed=outcome == "fail",
            skipped=outcome == "skip",
            longrepr=longrepr,
        ),
    )


def _store(tmp_path: Path) -> ResultStore:
    store = ResultStore(tmp_path, TARGET)
    store.start()
    return store


def _document(store: ResultStore) -> ResultDocument:
    return validate_document(json.loads(store.latest_path.read_text(encoding="utf-8")))


def test_resolve_target_default_and_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BASE_URL", raising=False)
    assert resolve_target() == DEFAULT_BASE_URL
    monkeypatch.setenv("BASE_URL", "https://example.test/app")
    assert resolve_target() == "https://example.test/app/"
    monkeypatch.setenv("BASE_URL", "   ")
    assert resolve_target() == DEFAULT_BASE_URL


def test_build_record_rejects_bad_status_and_pass_message() -> None:
    kwargs = {
        "run_id": "run-1",
        "recorded_at": "2026-09-30T17:00:00Z",
        "browser": "chromium",
        "case_id": NODE_ID,
        "description": "open the home page; expected: branding is visible",
        "target": TARGET,
        "url": TARGET,
        "action": "open the home page",
        "expectation": "branding is visible",
    }
    with pytest.raises(ValueError, match="status"):
        build_record(status="skipped", assertion_message=None, **kwargs)
    with pytest.raises(ValueError, match="assertion message"):
        build_record(status="pass", assertion_message="should not be here", **kwargs)


def test_partial_run_flushes_before_finish(tmp_path: Path) -> None:
    store = _store(tmp_path)
    item = _Item("chromium", url=TARGET)
    item.note("open the home page", "branding is visible")
    consume_report(store, _as_item(item), _report("call", "pass"))

    document = _document(store)
    assert document["run"]["status"] == "in_progress"
    assert document["run"]["finished_at"] is None
    records = document["records"]
    assert len(records) == 1
    assert records[0]["status"] == "pass"
    context = cast(dict[str, object], records[0]["context"])
    assert context["assertion_message"] is None
    assert context["url"] == TARGET
    assert records[0]["description"] == "open the home page; expected: branding is visible"


def test_same_case_keeps_one_record_per_browser(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for browser in ("chromium", "firefox"):
        item = _Item(browser, nodeid="tests/test_home_smoke.py::test_home")
        item.note("open the home page", "branding is visible")
        consume_report(store, _as_item(item), _report("call", "pass"))
    records = _document(store)["records"]
    assert [record["browser"] for record in records] == ["chromium", "firefox"]


def test_failure_stores_assertion_message_and_blank_url_falls_back(tmp_path: Path) -> None:
    store = _store(tmp_path)
    item = _Item("webkit", url="about:blank")
    item.note("open the home page", "hero is visible", url="https://www.kubozoa.com/services/")
    consume_report(
        store,
        _as_item(item),
        _report("call", "fail", "hero heading missing"),
    )
    record = _document(store)["records"][0]
    context = record["context"]
    assert record["status"] == "fail"
    assert record["browser"] == "webkit"
    assert context["url"] == "https://www.kubozoa.com/services/"
    assert context["assertion_message"] == "hero heading missing"


def test_setup_failure_and_skipped_call(tmp_path: Path) -> None:
    store = _store(tmp_path)
    def _open_home() -> None:
        """Open home and expect the hero."""

    item = _Item("firefox")
    item.obj = _open_home
    consume_report(store, _as_item(item), _report("setup", "fail", "browser failed to launch"))
    consume_report(store, _as_item(item), _report("call", "skip"))
    records = _document(store)["records"]
    assert len(records) == 1
    assert records[0]["status"] == "fail"
    context = records[0]["context"]
    assert context["assertion_message"] == "browser failed to launch"
    assert "Open home and expect the hero." in str(records[0]["description"])


def test_teardown_failure_upgrades_a_pass(tmp_path: Path) -> None:
    store = _store(tmp_path)
    item = _Item("chromium")
    item.note("open the home page", "branding is visible")
    consume_report(store, _as_item(item), _report("call", "pass"))
    consume_report(store, _as_item(item), _report("teardown", "fail", "context close failed"))
    record = _document(store)["records"][0]
    assert record["status"] == "fail"
    context = record["context"]
    assert context["assertion_message"] == "context close failed"


def test_non_browser_tests_are_not_stored(tmp_path: Path) -> None:
    store = _store(tmp_path)
    item = _Item("chromium")
    item.fixturenames = ["tmp_path"]
    consume_report(store, _as_item(item), _report("call", "pass"))
    assert _document(store)["records"] == []


def test_finish_marks_suite_and_keeps_earlier_run(tmp_path: Path) -> None:
    first = _store(tmp_path)
    item = _Item("chromium")
    item.note("open the home page", "branding is visible")
    consume_report(first, _as_item(item), _report("call", "pass"))
    first.finish(exitstatus=0)
    finished = _document(first)
    assert finished["run"]["status"] == "finished"
    assert finished["run"]["finished_at"]
    assert finished["records"][0]["run"]["finished_at"] == finished["run"]["finished_at"]
    archive = tmp_path / "runs" / f"{first.run_id}.json"
    assert json.loads(archive.read_text(encoding="utf-8"))["run"]["id"] == first.run_id

    second = ResultStore(tmp_path, TARGET)
    second.start()
    current = _document(second)
    assert current["run"]["status"] == "in_progress"
    assert current["records"] == []
    assert current["run"]["id"] != first.run_id
    assert json.loads(archive.read_text(encoding="utf-8"))["records"]


def test_interrupted_exit_is_not_a_finished_success(tmp_path: Path) -> None:
    store = _store(tmp_path)
    item = _Item("chromium")
    item.note("open the home page", "branding is visible")
    consume_report(store, _as_item(item), _report("call", "pass"))
    store.finish(exitstatus=2)
    document = _document(store)
    assert document["run"]["status"] == "interrupted"
    assert document["run"]["finished_at"]


def test_separate_process_can_read_the_file(tmp_path: Path) -> None:
    store = _store(tmp_path)
    item = _Item("firefox")
    item.note("open the home page", "branding is visible")
    consume_report(store, _as_item(item), _report("call", "fail", "logo missing"))
    store.finish(exitstatus=1)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json,sys; json.load(open(sys.argv[1], encoding='utf-8'))",
            str(store.latest_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    document = validate_document(json.loads(store.latest_path.read_text(encoding="utf-8")))
    assert document["records"][0]["status"] == "fail"


def test_validate_rejects_a_pass_that_includes_a_message(tmp_path: Path) -> None:
    store = _store(tmp_path)
    item = _Item("chromium")
    item.note("open the home page", "branding is visible")
    consume_report(store, _as_item(item), _report("call", "pass"))
    store.finish(exitstatus=0)
    document = _document(store)
    document["records"][0]["context"]["assertion_message"] = "not a failure"
    with pytest.raises(ValueError, match="assertion_message"):
        validate_document(document)


def test_failure_message_prefers_the_exception_text() -> None:
    report = cast(pytest.TestReport, SimpleNamespace(longrepr=None, failed=True))
    call = cast(
        pytest.CallInfo[None],
        SimpleNamespace(excinfo=SimpleNamespace(value=AssertionError("hero missing"))),
    )
    assert failure_message(report, call) == "hero missing"


def test_sample_json_matches_the_schema() -> None:
    path = Path(__file__).resolve().parents[1] / "results" / "sample.json"
    document = validate_document(json.loads(path.read_text(encoding="utf-8")))
    assert document["run"]["id"] == "sample"
    assert document["run"]["status"] == "finished"
    assert {record["status"] for record in document["records"]} == {"pass", "fail"}
    assert {record["browser"] for record in document["records"]} == {"chromium", "firefox"}
