(function () {
  "use strict";

  var app = document.querySelector("#app");
  var LATEST = "/results/latest.json";
  var SAMPLE = "/results/sample.json";
  var LATEST_LABEL = "results/latest.json";
  var SAMPLE_LABEL = "results/sample.json";

  load().catch(function (error) {
    renderError(LATEST_LABEL, "The dashboard could not load results. " + error.message);
  });

  function markCurrentSource(label) {
    var links = document.querySelectorAll(".sources a");
    for (var i = 0; i < links.length; i += 1) {
      links[i].removeAttribute("aria-current");
      var href = links[i].getAttribute("href") || "";
      var showsLatest = label === LATEST_LABEL && href.indexOf("file=latest") !== -1;
      var showsSample = label === SAMPLE_LABEL && href.indexOf("file=sample") !== -1;
      if (showsLatest || showsSample) {
        links[i].setAttribute("aria-current", "page");
      }
    }
  }

  function requestedFile() {
    var params = new URLSearchParams(window.location.search);
    if (!params.has("file")) {
      return null;
    }
    return (params.get("file") || "").trim();
  }

  function isAllowedLabel(file) {
    return /^(results|dashboard\/fixtures)\/(?:[A-Za-z0-9._-]+\/)*[A-Za-z0-9._-]+\.json$/.test(
      file
    );
  }

  function explicitSource(file) {
    if (file === "latest") {
      return { path: LATEST, label: LATEST_LABEL };
    }
    if (file === "sample") {
      return { path: SAMPLE, label: SAMPLE_LABEL };
    }
    if (!isAllowedLabel(file)) {
      return null;
    }
    return { path: "/" + file, label: file };
  }

  async function load() {
    var requested = requestedFile();
    if (requested === null) {
      await loadDefault();
      return;
    }
    if (requested === "") {
      renderError("(empty file query)", "Add a results path, or open Latest run or Sample file.");
      return;
    }
    var source = explicitSource(requested);
    if (!source) {
      renderError(
        requested,
        "That path is not a results JSON file. Use results/latest.json, results/sample.json, or a dashboard/fixtures JSON file."
      );
      return;
    }
    var loaded = await readSource(source.path, source.label);
    if (!loaded.ok) {
      renderProblem(source.label, loaded.problem);
      return;
    }
    renderDocument(source.label, loaded.document, null);
  }

  async function loadDefault() {
    var latest = await readSource(LATEST, LATEST_LABEL);
    if (latest.ok) {
      renderDocument(LATEST_LABEL, latest.document, null);
      return;
    }
    if (latest.problem.state !== "missing") {
      renderProblem(LATEST_LABEL, latest.problem);
      return;
    }
    var sample = await readSource(SAMPLE, SAMPLE_LABEL);
    if (!sample.ok) {
      renderProblem(LATEST_LABEL, {
        state: "missing",
        message:
          "results/latest.json was not found, and the sample file results/sample.json could not be read either. " +
          sample.problem.message,
      });
      return;
    }
    renderDocument(
      SAMPLE_LABEL,
      sample.document,
      "results/latest.json was not found. Showing the committed example results/sample.json."
    );
  }

  async function readSource(path, label) {
    var response;
    try {
      response = await fetch(path, { cache: "no-store" });
    } catch (error) {
      return {
        ok: false,
        problem: {
          state: "invalid",
          message: "The browser could not fetch " + label + ".",
        },
      };
    }
    if (response.status === 404) {
      return {
        ok: false,
        problem: { state: "missing", message: label + " was not found." },
      };
    }
    if (!response.ok) {
      return {
        ok: false,
        problem: {
          state: "invalid",
          message: label + " could not be read (HTTP " + response.status + ").",
        },
      };
    }
    var text = await response.text();
    var parsed = parseDocument(text);
    if (!parsed.ok) {
      return { ok: false, problem: parsed.problem };
    }
    return { ok: true, document: parsed.document };
  }

  function parseDocument(text) {
    if (text.trim() === "") {
      return {
        ok: false,
        problem: { state: "empty", message: "The file is empty." },
      };
    }
    var data;
    try {
      data = JSON.parse(text);
    } catch (error) {
      return {
        ok: false,
        problem: { state: "invalid", message: "The file is not valid JSON." },
      };
    }
    var problem = validateDocument(data);
    if (problem) {
      return { ok: false, problem: { state: "invalid", message: problem } };
    }
    return { ok: true, document: data };
  }

  function validateDocument(data) {
    if (Array.isArray(data)) {
      return "The file is a bare array. Schema version 1 is an object with schema_version, run, target, and records.";
    }
    if (!data || typeof data !== "object") {
      return "The file must be a JSON object.";
    }
    if (data.schema_version !== 1) {
      return "schema_version must be 1.";
    }
    if (!data.run || typeof data.run !== "object" || Array.isArray(data.run)) {
      return "run must be an object.";
    }
    if (!nonEmptyString(data.run.id)) {
      return "run.id must be a non-empty string.";
    }
    if (!nonEmptyString(data.run.status)) {
      return "run.status must be a non-empty string.";
    }
    if (!nonEmptyString(data.target)) {
      return "target must be a non-empty string.";
    }
    if (!Array.isArray(data.records)) {
      return "records must be an array.";
    }
    for (var i = 0; i < data.records.length; i += 1) {
      var recordProblem = validateRecord(data.records[i], i);
      if (recordProblem) {
        return recordProblem;
      }
    }
    return null;
  }

  function validateRecord(record, index) {
    var label = "records[" + index + "]";
    if (!record || typeof record !== "object" || Array.isArray(record)) {
      return label + " must be an object.";
    }
    if (!nonEmptyString(record.case_id)) {
      return label + ".case_id must be a non-empty string.";
    }
    if (!nonEmptyString(record.description)) {
      return label + ".description must be a non-empty string.";
    }
    if (record.status !== "pass" && record.status !== "fail") {
      return label + ".status must be pass or fail.";
    }
    if (!nonEmptyString(record.browser)) {
      return label + ".browser must be a non-empty string.";
    }
    var context = record.context;
    if (!context || typeof context !== "object" || Array.isArray(context)) {
      return label + ".context must be an object.";
    }
    if (!nonEmptyString(context.url)) {
      return label + ".context.url must be a non-empty string.";
    }
    if (!nonEmptyString(context.action)) {
      return label + ".context.action must be a non-empty string.";
    }
    if (!nonEmptyString(context.expectation)) {
      return label + ".context.expectation must be a non-empty string.";
    }
    var message = context.assertion_message;
    if (record.status === "pass" && message !== null) {
      return label + " pass records must have assertion_message null.";
    }
    if (record.status === "fail" && !nonEmptyString(message)) {
      return label + " fail records must include assertion_message.";
    }
    return null;
  }

  function nonEmptyString(value) {
    return typeof value === "string" && value.trim() !== "";
  }

  function renderProblem(label, problem) {
    var title = "Could not show results";
    if (problem.state === "missing") {
      title = "Results file not found";
    } else if (problem.state === "empty") {
      title = "Results file is empty";
    } else if (problem.state === "invalid") {
      title = "Results file is invalid";
    }
    clear(app);
    markCurrentSource(label);
    app.appendChild(banner("banner-error", title, label + ": " + problem.message));
    var note = document.createElement("p");
    note.className = "hint";
    note.textContent =
      "No pass or fail list is shown for this file. Fix the file, or open Latest run or Sample file.";
    app.appendChild(note);
    document.title = "Browser test results — " + title;
  }

  function renderError(label, message) {
    renderProblem(label, { state: "invalid", message: message });
  }

  function renderDocument(label, document, notice) {
    clear(app);
    markCurrentSource(label);
    if (notice) {
      app.appendChild(banner("banner-info", "Sample fallback", notice));
    }

    var records = document.records;
    var passed = 0;
    var failed = 0;
    for (var i = 0; i < records.length; i += 1) {
      if (records[i].status === "fail") {
        failed += 1;
      } else {
        passed += 1;
      }
    }

    app.appendChild(runMeta(label, document));
    app.appendChild(counts(records.length, passed, failed));

    if (failed > 0) {
      var noun = failed === 1 ? "failure is" : "failures are";
      app.appendChild(
        banner(
          "banner-fail",
          failed + " " + (failed === 1 ? "failure" : "failures"),
          "The " + noun + " listed with the other cases below. Open a failed row for the browser, URL, action, expectation, and failure message."
        )
      );
    }

    if (records.length === 0) {
      var empty = document.createElement("section");
      empty.className = "panel empty-state";
      var heading = document.createElement("h2");
      heading.textContent = "No case results";
      var copy = document.createElement("p");
      copy.textContent =
        "This file has no case × browser records. Nothing passed or failed. This is not a passing run.";
      empty.appendChild(heading);
      empty.appendChild(copy);
      app.appendChild(empty);
      document.title = "Browser test results — no records";
      return;
    }

    var list = document.createElement("div");
    list.className = "records";
    for (var index = 0; index < records.length; index += 1) {
      list.appendChild(recordCard(records[index], index));
    }
    app.appendChild(list);
    document.title =
      "Browser test results — " + passed + " pass, " + failed + " fail";
  }

  function runMeta(label, document) {
    var run = document.run;
    var dl = document.createElement("dl");
    dl.className = "run-meta";
    appendMeta(dl, "File", label);
    appendMeta(dl, "Run", textOrDash(run.id));
    appendMeta(dl, "Run status", textOrDash(run.status));
    appendMeta(dl, "Finished", textOrDash(run.finished_at));
    appendMeta(dl, "Target", textOrDash(document.target));
    return dl;
  }

  function appendMeta(dl, name, value) {
    var dt = document.createElement("dt");
    dt.textContent = name;
    var dd = document.createElement("dd");
    dd.textContent = value;
    var wrap = document.createElement("div");
    wrap.appendChild(dt);
    wrap.appendChild(dd);
    dl.appendChild(wrap);
  }

  function counts(total, passed, failed) {
    var row = document.createElement("p");
    row.className = "counts";
    row.appendChild(chip("count", total + (total === 1 ? " record" : " records")));
    row.appendChild(chip("count count-pass", passed + " pass"));
    row.appendChild(chip("count count-fail", failed + " fail"));
    return row;
  }

  function chip(className, text) {
    var span = document.createElement("span");
    span.className = className;
    span.textContent = text;
    return span;
  }

  function recordCard(record, index) {
    var failed = record.status === "fail";
    var article = document.createElement("article");
    article.className = "record " + (failed ? "record-fail" : "record-pass");
    article.id = "record-" + index;

    var head = document.createElement("div");
    head.className = "record-head";

    var status = document.createElement("p");
    status.className = "status " + (failed ? "status-fail" : "status-pass");
    status.textContent = failed ? "Fail" : "Pass";

    var body = document.createElement("div");
    body.className = "record-body";

    var caseId = document.createElement("h2");
    caseId.className = "case-id";
    caseId.textContent = record.case_id;

    var browser = document.createElement("p");
    browser.className = "browser";
    browser.textContent = "Browser: " + record.browser;

    var description = document.createElement("p");
    description.className = "description";
    description.textContent = record.description;

    body.appendChild(caseId);
    body.appendChild(browser);
    body.appendChild(description);
    head.appendChild(status);
    head.appendChild(body);
    article.appendChild(head);

    if (failed) {
      article.appendChild(failureDetails(record, index));
    }
    return article;
  }

  function failureDetails(record, index) {
    var context = record.context;
    var button = document.createElement("button");
    button.type = "button";
    button.className = "toggle";
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-controls", "failure-" + index);
    button.textContent = "Show failure details";

    var panel = document.createElement("div");
    panel.id = "failure-" + index;
    panel.hidden = true;

    var dl = document.createElement("dl");
    dl.className = "context";
    appendContext(dl, "Browser", record.browser, false);
    appendContext(dl, "URL", context.url, false);
    appendContext(dl, "Action", context.action, false);
    appendContext(dl, "Expectation", context.expectation, false);
    appendContext(dl, "Failure message", context.assertion_message, true);
    panel.appendChild(dl);

    button.addEventListener("click", function () {
      var open = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", open ? "false" : "true");
      button.textContent = open ? "Show failure details" : "Hide failure details";
      panel.hidden = open;
    });

    var wrap = document.createElement("div");
    wrap.className = "details";
    wrap.appendChild(button);
    wrap.appendChild(panel);
    return wrap;
  }

  function appendContext(dl, name, value, isFailure) {
    var dt = document.createElement("dt");
    dt.textContent = name;
    var dd = document.createElement("dd");
    if (isFailure) {
      dd.className = "failure-message";
    }
    if (name === "URL") {
      var href = httpUrl(value);
      if (href) {
        var link = document.createElement("a");
        link.href = href;
        link.textContent = value;
        dd.appendChild(link);
      } else {
        dd.textContent = value;
      }
    } else {
      dd.textContent = value;
    }
    dl.appendChild(dt);
    dl.appendChild(dd);
  }

  function httpUrl(value) {
    try {
      var url = new URL(value);
      if (url.protocol === "http:" || url.protocol === "https:") {
        return url.href;
      }
    } catch (error) {
      return null;
    }
    return null;
  }

  function banner(className, title, message) {
    var box = document.createElement("section");
    box.className = "banner " + className;
    box.setAttribute("role", className.indexOf("error") === -1 ? "status" : "alert");
    var heading = document.createElement("h2");
    heading.textContent = title;
    var copy = document.createElement("p");
    copy.textContent = message;
    box.appendChild(heading);
    box.appendChild(copy);
    return box;
  }

  function textOrDash(value) {
    if (value === null || value === undefined || value === "") {
      return "—";
    }
    return String(value);
  }

  function clear(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }
})();
