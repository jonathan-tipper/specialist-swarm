/* War-Room Bridge — event-driven board.
   handleEvent() is the only place that knows the SSE wire format; everything
   below it works on board state (agents, phases, clock). */

(() => {
  "use strict";

  // ---------- element refs ----------
  const $ = (id) => document.getElementById(id);
  const startBtn = $("start");
  const clockEl = $("clock");
  const clockTime = $("clock-time");
  const narration = $("narration");
  const transcript = $("transcript");
  const outcome = $("outcome");
  const statusline = $("statusline");
  const connectorsSvg = $("connectors");
  const commanderCard = $("agent-commander");
  const commanderStatus = $("commander-status");
  const commanderDetail = $("commander-detail");

  const SPECIALISTS = {
    "SRE Responder": $("agent-sre"),
    "Security Analyst": $("agent-security"),
    "Comms Lead": $("agent-comms"),
  };
  const HUES = {
    "SRE Responder": "#4dd0e1",
    "Security Analyst": "#b48cf2",
    "Comms Lead": "#f0b429",
  };

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- run state ----------
  let startedAt = null;
  let clockTimer = null;
  let taskedCount = 0;
  let reportedCount = 0;
  let consoleUrl = null;
  let source = null;

  // ---------- clock ----------
  const elapsed = () => {
    if (!startedAt) return "--:--";
    const s = Math.floor((Date.now() - startedAt) / 1000);
    return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  };

  function startClock() {
    startedAt = Date.now();
    clockEl.classList.add("running");
    clockTimer = setInterval(() => { clockTime.textContent = elapsed(); }, 1000);
    clockTime.textContent = "00:00";
  }

  function stopClock() {
    clearInterval(clockTimer);
    clockEl.classList.remove("running");
  }

  // ---------- phases ----------
  function setPhase(name, state) {
    const el = document.querySelector(`.phase[data-phase="${name}"]`);
    if (el) { el.classList.remove("active", "done"); if (state) el.classList.add(state); }
  }

  // ---------- transcript & narration ----------
  function logRow(text, cls) {
    if (transcript.querySelector(".placeholder")) transcript.innerHTML = "";
    const row = document.createElement("div");
    row.className = "transcript-row";
    const t = document.createElement("span");
    t.className = "t";
    t.textContent = elapsed();
    const body = document.createElement("span");
    if (cls) body.className = cls;
    body.textContent = text;
    row.append(t, body);
    transcript.appendChild(row);
    transcript.scrollTop = transcript.scrollHeight;
  }

  function narrate(text) {
    const ph = narration.querySelector(".placeholder");
    if (ph) narration.innerHTML = "";
    narration.appendChild(document.createTextNode(text));
    narration.scrollTop = narration.scrollHeight;
  }

  // ---------- agent cards ----------
  function setCommander(status, detail) {
    commanderStatus.textContent = status;
    if (detail) commanderDetail.textContent = detail;
  }

  function setCardState(card, state) { card.dataset.status = state; }

  function stamp(card, label) {
    const li = document.createElement("li");
    const t = document.createElement("span");
    t.className = "t";
    t.textContent = elapsed();
    li.append(t, document.createTextNode(label));
    card.querySelector(".agent-times").appendChild(li);
  }

  function setSpecialist(name, status, state, stampLabel) {
    const card = SPECIALISTS[name];
    if (!card) return;
    card.querySelector(".agent-status").textContent = status;
    setCardState(card, state);
    if (stampLabel) stamp(card, stampLabel);
  }

  // ---------- connectors ----------
  const paths = {}; // agent name -> SVG path element

  function drawConnectors() {
    connectorsSvg.innerHTML = "";
    const boardBox = $("board").getBoundingClientRect();
    const from = commanderCard.getBoundingClientRect();
    const x1 = from.left + from.width / 2 - boardBox.left;
    const y1 = from.bottom - boardBox.top;

    for (const [name, card] of Object.entries(SPECIALISTS)) {
      const to = card.getBoundingClientRect();
      const x2 = to.left + to.width / 2 - boardBox.left;
      const y2 = to.top - boardBox.top;
      const midY = (y1 + y2) / 2;
      const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
      p.setAttribute("d", `M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`);
      p.classList.add("connector-path");
      // carry over live/done state on redraw
      if (paths[name]) p.classList.add(...paths[name].classList);
      connectorsSvg.appendChild(p);
      paths[name] = p;
    }
  }

  function pulseAlong(name, reverse) {
    const path = paths[name];
    if (!path || reducedMotion) return;
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.classList.add("connector-pulse");
    dot.setAttribute("fill", HUES[name] || "#6ea8ff");
    connectorsSvg.appendChild(dot);
    const len = path.getTotalLength();
    const t0 = performance.now();
    const DURATION = 650;
    (function step(now) {
      const k = Math.min((now - t0) / DURATION, 1);
      const pt = path.getPointAtLength(len * (reverse ? 1 - k : k));
      dot.setAttribute("cx", pt.x);
      dot.setAttribute("cy", pt.y);
      if (k < 1) requestAnimationFrame(step); else dot.remove();
    })(t0);
  }

  function connectorState(name, cls) {
    const p = paths[name];
    if (p) { p.classList.remove("live", "done"); if (cls) p.classList.add(cls); }
  }

  // ---------- outcome ----------
  function showOutcome({ ok, title, sub, links }) {
    outcome.hidden = false;
    outcome.innerHTML = "";
    const card = document.createElement("div");
    card.className = "outcome-card" + (ok ? "" : " failed");
    const txt = document.createElement("div");
    const h = document.createElement("p");
    h.className = "outcome-title";
    h.textContent = title;
    const s = document.createElement("p");
    s.className = "outcome-sub";
    s.textContent = sub;
    txt.append(h, s);
    const spacer = document.createElement("div");
    spacer.className = "outcome-spacer";
    card.append(txt, spacer);
    for (const { href, label, primary, external } of links) {
      const a = document.createElement("a");
      a.href = href;
      a.textContent = label;
      if (primary) a.className = "primary";
      if (external) a.target = "_blank";
      card.appendChild(a);
    }
    outcome.appendChild(card);
  }

  // ---------- board reset ----------
  function resetBoard() {
    taskedCount = 0;
    reportedCount = 0;
    consoleUrl = null;
    outcome.hidden = true;
    outcome.innerHTML = "";
    narration.innerHTML = '<p class="placeholder">The commander’s reasoning appears here.</p>';
    transcript.innerHTML = '<p class="placeholder">Raw event feed. Nothing on the wire yet.</p>';
    statusline.className = "statusline";
    document.querySelectorAll(".phase").forEach((p) => p.classList.remove("active", "done"));
    setCardState(commanderCard, "standby");
    setCommander("Standby", "Waiting for the page.");
    for (const [name, card] of Object.entries(SPECIALISTS)) {
      card.querySelector(".agent-status").textContent = "Standby";
      card.querySelector(".agent-times").innerHTML = "";
      setCardState(card, "standby");
      connectorState(name, null);
    }
  }

  // ---------- milestones ----------
  function onAllTasked() {
    setPhase("fanout", "done");
    setPhase("investigation", "active");
    setCommander("Awaiting reports · 0/3", "All three specialists briefed and investigating in parallel.");
    logRow("— all three specialists briefed in parallel —", "tr-milestone");
  }

  function onAllReported() {
    setPhase("investigation", "done");
    setPhase("reconciliation", "active");
    setCommander("Reconciling", "Weighing the deploy against the traffic anomaly. Two causes, one cause seen twice, or cause plus coincidence?");
    logRow("— all reports in; commander reconciling —", "tr-milestone");
  }

  // ---------- the one place that knows the wire format ----------
  function handleEvent(ev) {
    switch (ev.kind) {
      case "session_started": {
        consoleUrl = ev.console_url;
        setPhase("intake", "active");
        setCardState(commanderCard, "working");
        setCommander("Reading intake", "Reading the ticket, topology, change log and prior incidents before briefing anyone.");
        logRow(`session ${ev.session_id}`, "tr-milestone");
        statusline.textContent = "Bridge open. Commander reading intake.";
        break;
      }
      case "thread": {
        if (ev.agent in SPECIALISTS) {
          if (ev.event === "created") {
            setSpecialist(ev.agent, "On the bridge", "working", "joined the bridge");
            connectorState(ev.agent, "live");
          } else {
            setSpecialist(ev.agent, "Investigating", "working", null);
          }
        }
        logRow(`${ev.event === "created" ? "on the bridge" : "investigating"} · ${ev.agent}`, "tr-thread");
        break;
      }
      case "dispatch": {
        if (ev.direction === "tasked") {
          taskedCount += 1;
          if (taskedCount === 1) { setPhase("intake", "done"); setPhase("fanout", "active"); setCommander("Briefing specialists", "Fanning the incident out — each specialist gets the ticket plus a narrow brief."); }
          setSpecialist(ev.agent, "Briefed", "working", "briefed by commander");
          pulseAlong(ev.agent, false);
          logRow(`tasked → ${ev.agent}`, "tr-tasked");
          if (taskedCount === 3) onAllTasked();
        } else {
          reportedCount += 1;
          setSpecialist(ev.agent, "Reported", "done", "report delivered");
          connectorState(ev.agent, "done");
          pulseAlong(ev.agent, true);
          logRow(`reported ← ${ev.agent}`, "tr-reported");
          if (reportedCount < 3) setCommander(`Awaiting reports · ${reportedCount}/3`);
          else onAllReported();
        }
        break;
      }
      case "tool": {
        if (reportedCount === 3) {
          setPhase("reconciliation", "done");
          setPhase("postmortem", "active");
          setCommander("Writing postmortem", "Findings reconciled. Writing the blameless postmortem with the docx skill.");
        }
        logRow(`tool · ${ev.name}`, "tr-tool");
        break;
      }
      case "commander_text": {
        narrate(ev.text);
        break;
      }
      case "terminated": {
        logRow("— bridge closed —", "tr-milestone");
        break;
      }
      case "outputs": {
        stopClock();
        setCardState(commanderCard, "done");
        const links = [];
        if (consoleUrl) links.push({ href: consoleUrl, label: "View full session", external: true });
        if (ev.files.length) {
          document.querySelectorAll(".phase").forEach((p) => { p.classList.remove("active"); p.classList.add("done"); });
          setCommander("Postmortem delivered", "Blameless postmortem written and downloaded. Bridge closed.");
          for (const f of ev.files) links.unshift({ href: `/outputs/${encodeURIComponent(f)}`, label: `Download ${f}`, primary: true });
          showOutcome({ ok: true, title: "Postmortem delivered", sub: `Bridge ran ${elapsed()} · 3 specialists · 1 reconciled root cause`, links });
          statusline.textContent = `Run complete in ${elapsed()}.`;
        } else {
          setCommander("Closed without artifact", "The commander replied in chat instead of writing the document.");
          showOutcome({ ok: false, title: "No files produced", sub: "The commander may have replied in chat instead of using the docx skill — check the session trace.", links });
          statusline.textContent = "Run ended with no files.";
        }
        finishRun();
        break;
      }
      case "error": {
        stopClock();
        logRow(ev.message, "tr-error");
        statusline.textContent = ev.message;
        statusline.classList.add("error");
        showOutcome({ ok: false, title: "Run failed", sub: ev.message, links: consoleUrl ? [{ href: consoleUrl, label: "View session", external: true }] : [] });
        finishRun();
        break;
      }
    }
  }

  function finishRun() {
    if (source) source.close();
    source = null;
    startBtn.disabled = false;
    startBtn.textContent = "Run it again";
  }

  // ---------- start ----------
  startBtn.addEventListener("click", () => {
    resetBoard();
    startBtn.disabled = true;
    startBtn.textContent = "Bridge open…";
    startClock();
    drawConnectors();
    statusline.textContent = "Opening the bridge…";

    source = new EventSource("/events");
    source.onmessage = (e) => handleEvent(JSON.parse(e.data));
    source.onerror = () => {
      handleEvent({ kind: "error", message: "Lost connection to the server. Is webapp.py still running?" });
    };
  });

  window.addEventListener("resize", drawConnectors);
  drawConnectors();

  // Debug/demo hook: replay a bridge without a live run.
  window.__bridge = { handleEvent, resetBoard, startClock, drawConnectors };
})();
