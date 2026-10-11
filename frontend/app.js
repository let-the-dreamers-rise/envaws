const API = (window.CLEANHOUR_API || "").replace(/\/$/, "");
const params = new URLSearchParams(location.search);
const SID = params.get("school") || "demo-rohini";
const REPLAY = "2025-11-21";
const HEAT_REPLAY = "2025-04-08";
const REPLAYS = { [REPLAY]: "Smog replay · 21 Nov 2025", [HEAT_REPLAY]: "Heat replay · 8 Apr 2025" };
const BANDS = [
  ["Good", "#2e9e4f"], ["Satisfactory", "#8cc43f"], ["Moderate", "#f4c430"],
  ["Poor", "#f08a24"], ["Very Poor", "#d93b3b"], ["Severe", "#7e1f3c"],
];
const FLAG_ICON = { good: "🟢", satisfactory: "🟢", moderate: "🟡", poor: "🟠", very_poor: "🔴", severe: "🟣" };
const STATUS_TEXT = {
  planning: "Planning…", pending_approval: "Awaiting your approval", approved: "Approved · publishing",
  published: "Published to parents", expired: "Expired (not approved)",
};

const state = { school: null, date: null, view: "after", lang: "hi", item: null, busy: false };
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    method: opts.method || "GET",
    headers: opts.body ? { "content-type": "application/json" } : {},
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { const e = new Error(data.error || res.statusText); e.status = res.status; throw e; }
  return data;
}

function toast(msg, ms = 2600) {
  const t = $("toast"); t.textContent = msg; t.classList.remove("hidden");
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.add("hidden"), ms);
}

function istDate(offsetDays = 0) {
  const d = new Date(Date.now() + 5.5 * 3600e3 + offsetDays * 86400e3);
  return d.toISOString().slice(0, 10);
}

function clock(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`;
}

function dayLabel(iso, i) {
  if (REPLAYS[iso]) return REPLAYS[iso];
  if (i === 0) return "Today";
  if (i === 1) return "Tomorrow";
  return new Date(iso + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
}

function renderDays() {
  const days = [0, 1, 2, 3].map(istDate).concat([REPLAY, HEAT_REPLAY]);
  $("days").innerHTML = days.map((d, i) =>
    `<button class="chip${REPLAYS[d] ? " replay" : ""}" data-date="${d}" aria-pressed="${d === state.date}">${esc(dayLabel(d, i))}</button>`).join("");
  $("days").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => selectDay(b.dataset.date)));
}

async function selectDay(date) {
  state.date = date;
  renderDays();
  history.replaceState(null, "", `?school=${SID}&date=${date}`);
  try {
    state.item = await api(`/api/schools/${SID}/plans/${date}`);
  } catch (e) {
    state.item = null;
  }
  render();
}

async function runCheck() {
  if (state.busy) return;
  state.busy = true; render();
  try {
    const when = state.date;
    let item = await api(`/api/schools/${SID}/plans`, { method: "POST", body: { when } });
    item = await waitWhile(item, ["planning"]);
    state.item = item;
  } catch (e) {
    toast(`Couldn't plan: ${e.message}`, 5000);
  } finally {
    state.busy = false; render(); loadLog();
  }
}

async function waitWhile(item, statuses, maxMs = 90000) {
  const start = Date.now();
  while (statuses.includes(item.status) && Date.now() - start < maxMs) {
    await sleep(1200);
    try { item = await api(`/api/schools/${SID}/plans/${item.date}`); } catch (e) { /* retry */ }
  }
  return item;
}

async function approve() {
  if (state.busy || !state.item) return;
  state.busy = true; render();
  try {
    let item;
    for (let i = 0; i < 8; i++) {
      try { item = await api(`/api/schools/${SID}/plans/${state.date}/approve`, { method: "POST", body: { by: "Principal" } }); break; }
      catch (e) { if (e.status === 409 && /retry/.test(e.message)) { await sleep(1000); continue; } throw e; }
    }
    state.item = await waitWhile(item, ["approved"]);
    toast("Published. Share it with parents.");
  } catch (e) {
    toast(`Couldn't approve: ${e.message}`, 5000);
  } finally {
    state.busy = false; render(); loadLog();
  }
}

async function setGrap(stage) {
  try {
    state.school = await api(`/api/schools/${SID}/grap`, { method: "POST", body: { stage: Number(stage) } });
    toast(`GRAP stage set to ${["none", "I", "II", "III", "IV"][stage]}. Re-planning…`);
    await runCheck();
  } catch (e) { toast(e.message); }
}

function render() {
  const plan = state.item && state.item.plan;
  renderHero(plan);
  ["airCard", "ttCard", "changesCard", "approveCard"].forEach((id) => $(id).classList.toggle("hidden", !plan));
  if (!plan) return;
  renderStrip(plan);
  renderTimetable(plan);
  renderChanges(plan);
  renderApprove(plan);
}

function renderHero(plan) {
  const hero = $("hero");
  if (!plan) {
    const intro = {
      [REPLAY]: "Replay 21 Nov 2025: the smog week the Supreme Court called outdoor activity a “gas chamber”",
      [HEAT_REPLAY]: "Replay 8 Apr 2025: Delhi's first heatwave of the year. Same school, same engine.",
    }[state.date];
    hero.innerHTML = `<div class="empty">
      <div class="big">${intro || "No plan for this day yet"}</div>
      <p>CleanHour runs automatically at 5:30 AM IST. You can run the check now.</p>
      <button class="btn primary" id="runBtn" ${state.busy ? "disabled" : ""}>${state.busy ? '<span class="spin"></span> Planning…' : "Run the 5:30 AM check"}</button>
    </div>`;
    $("runBtn").addEventListener("click", runCheck);
    return;
  }
  const f = plan.flag, m = plan.metrics, idx = plan.period_index;
  const status = state.item.status;
  const hot = plan.heat && plan.heat.feels >= 37;
  const what = hot ? `Heat day · ${f.en} air` : `${f.en} air`;
  const headline = plan.quiet ? `${what} · normal timetable` : `${what} · ${plan.changes.length} change${plan.changes.length === 1 ? "" : "s"}`;
  const heat = plan.heat && plan.heat.feels >= 35 ? ` · Feels like ${plan.heat.feels} °C at ${clock(idx[plan.heat.period].start)}` : "";
  const heatMetric = m.heat_moves > 0;
  hero.innerHTML = `
    <div class="hero-band" style="background:${hot ? "#e0622a" : f.colour}">
      <div class="flag" aria-hidden="true">${hot ? "☀️" : FLAG_ICON[f.key] || "⚪"}</div>
      <div>
        <div class="title">${esc(headline)}</div>
        <div class="sub">Worst: PM2.5 ${f.pm25} at ${clock(idx[f.period].start)}${heat} · ${plan.mode === "replay" ? "Replay of " : ""}${new Date(plan.date + "T00:00:00").toDateString()} · GRAP ${["none", "I", "II", "III", "IV"][plan.grap_stage]}</div>
      </div>
      <span class="status-pill">${esc(STATUS_TEXT[status] || status)}</span>
    </div>
    <div class="metrics">
      ${heatMetric
        ? `<div class="metric"><div class="v good">${m.pe_feels_before}° → ${m.pe_feels_after}°</div><div class="l">Hottest PE, feels-like °C</div></div>
           <div class="metric"><div class="v">${m.reduction_pct > 0 ? "−" + m.reduction_pct + "%" : "0%"}</div><div class="l">PM2.5 breathed outdoors (est.)</div></div>`
        : `<div class="metric"><div class="v good">${m.reduction_pct > 0 ? "−" + m.reduction_pct + "%" : "0%"}</div><div class="l">PM2.5 breathed during outdoor time (est.)</div></div>
           <div class="metric"><div class="v">${m.pe_pm25_before} → ${m.pe_pm25_after}</div><div class="l">Avg PM2.5 during PE</div></div>`}
      <div class="metric"><div class="v">${m.pe_moved}${m.pe_indoor ? ` <small>+${m.pe_indoor} in</small>` : ""}</div><div class="l">PE periods moved${m.pe_indoor ? " / indoors" : ""}</div></div>
      <div class="metric"><div class="v">${m.asthma_kids_indoor}</div><div class="l">Asthma-watch kids kept in</div></div>
    </div>
    <div style="padding:12px 16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center">
      <button class="btn" id="rerunBtn" ${state.busy ? "disabled" : ""}>${state.busy ? '<span class="spin"></span> Planning…' : "↻ Re-run check"}</button>
      <span class="note">Plan generated ${new Date(plan.generated_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })} IST</span>
    </div>`;
  $("rerunBtn").addEventListener("click", runCheck);
}

function renderStrip(plan) {
  const max = Math.max(150, ...plan.periods.map((p) => p.pm25));
  $("strip").innerHTML = plan.periods.map((p) => `
    <div class="bar" title="${esc(p.label)} ${p.start}-${p.end}: PM2.5 ${p.pm25} (${esc(p.band.en)})">
      <div class="val">${p.pm25}</div>
      <div class="fill" style="height:${Math.max(4, (p.pm25 / max) * 100)}%;background:${p.band.colour}"></div>
      <div class="lbl">${esc(p.id === "ASM" ? "Assembly" : p.id === "REC" ? "Recess" : p.id)}<br>${p.start}${p.feels != null ? `<br><b class="feels">${p.feels}°</b>` : ""}</div>
    </div>`).join("");
  $("legend").innerHTML = BANDS.map(([n, c]) => `<span style="--c:${c}">${n}</span>`).join("");
  $("forecastSource").textContent = `Source: ${plan.forecast.source}`;
}

function renderTimetable(plan) {
  const tt = state.view === "after" ? plan.timetable_after : plan.timetable_before;
  const periods = plan.periods;
  const pm = Object.fromEntries(periods.map((p) => [p.id, p]));
  const venue = {};
  plan.changes.filter((c) => c.type === "venue").forEach((c) => {
    (c.scope === "all" ? Object.keys(tt) : c.scope).forEach((cid) => { venue[`${c.activity}|${cid}`] = true; });
  });
  const asthma = Object.fromEntries(plan.changes.filter((c) => c.type === "asthma").map((c) => [c.class_id, c.count]));
  const head = `<tr><th></th>${periods.map((p) => `<th>${esc(p.id === "ASM" ? "Assembly" : p.id === "REC" ? "Recess" : p.id)} <span class="t">${p.start}</span><span class="pm" style="color:${p.band.colour}">${p.pm25}</span></th>`).join("")}</tr>`;
  const rows = Object.entries(tt).map(([cid, row]) => {
    const cells = periods.map((p) => {
      if (p.kind === "assembly" || p.kind === "recess") {
        const act = p.kind === "assembly" ? "Assembly" : "Recess";
        const indoor = state.view === "after" && venue[`${act}|${cid}`];
        const unsafe = state.view === "before" && plan.changes.some((c) => c.type === "venue" && c.activity === act && (c.scope === "all" || c.scope.includes(cid)));
        return `<td class="${indoor ? "indoor" : unsafe ? "bad" : ""}">${act}<span class="t">${indoor ? "indoors" : "outdoors"}</span></td>`;
      }
      const cell = row[p.id];
      const isPE = cell.subject === "PE";
      let cls = "";
      if (isPE) cls = isUnsafe(plan, cid, p.id) ? "bad" : "out";
      if (cell.indoor_from) cls = "indoor";
      if (!isPE && cell.moved_from) cls = "swapped";
      const tag = state.view === "after" && cell.moved_from ? `<span class="tag">${isPE ? "moved from" : "swapped from"} ${esc(cell.moved_from)}</span>` : "";
      const asth = state.view === "after" && isPE && asthma[cid] ? `<span class="tag">${asthma[cid]} asthma-watch in</span>` : "";
      return `<td class="${cls}">${esc(cell.subject)}<span class="t">${esc(cell.teacher)}</span>${tag}${asth}</td>`;
    }).join("");
    return `<tr><td class="cls">${esc(cid)}</td>${cells}</tr>`;
  }).join("");
  $("tt").innerHTML = `<thead>${head}</thead><tbody>${rows}</tbody>`;
  $("viewBefore").setAttribute("aria-pressed", state.view === "before");
  $("viewAfter").setAttribute("aria-pressed", state.view === "after");
}

function isUnsafe(plan, cid, pid) {
  // A PE cell is "bad" in the original timetable if CleanHour had to act on it.
  if (state.view === "after") return false;
  return plan.changes.some((c) => (c.type === "move" && c.class_id === cid && c.from === pid) || (c.type === "indoor" && c.class_id === cid && c.period === pid));
}

function ruleChips(plan, ids) {
  return `<div class="rules">${ids.map((r) => `<span class="rule${r.startsWith("grap") ? " reg" : ""}" title="${esc(r)}">${esc((plan.rule_text[r] || [r])[0])}</span>`).join("")}</div>`;
}

function skippedText(plan, skipped) {
  if (!skipped || !skipped.length) return "";
  const why = skipped.slice(0, 3).map((s) => {
    const when = clock(plan.period_index[s.period].start);
    if (s.why === "ground_full") return `${when}: playground full`;
    if (s.why === "teacher_busy") return `${when}: ${s.teacher} teaching ${s.with}`;
    return `${when}: rules`;
  });
  return `<div class="skip">Not used: ${esc(why.join(" · "))}</div>`;
}

function renderChanges(plan) {
  const idx = plan.period_index;
  if (plan.quiet) {
    $("changes").innerHTML = `<p class="note">Air stays ${esc(plan.flag.en)} or better through school hours, so CleanHour leaves the timetable alone. No alert fatigue.</p>`;
    return;
  }
  const order = { venue: 0, indoor: 1, move: 2, asthma: 3 };
  $("changes").innerHTML = [...plan.changes].sort((a, b) => order[a.type] - order[b.type]).map((c) => {
    if (c.type === "move") {
      return `<div class="change"><div class="ic">⏱</div><div>
        <div class="h">${esc(c.class_id)} PE: ${clock(idx[c.from].start)} → ${clock(idx[c.to].start)}${c.driver === "heat" ? " · heat" : ""}</div>
        <div class="d">${c.driver === "heat"
          ? `Feels like ${c.feels_from} → ${c.feels_to} °C (${c.feels_from - c.feels_to}° cooler).`
          : `PM2.5 ${c.pm25_from} → ${c.pm25_to} (${c.gain_pct}% cleaner).`} ${esc(c.swapped.subject)} (${esc(c.swapped.teacher)}) takes the ${idx[c.to].start < idx[c.from].start ? "later" : "earlier"} slot.</div>
        ${ruleChips(plan, c.rules)}${skippedText(plan, c.skipped)}</div></div>`;
    }
    if (c.type === "indoor") {
      return `<div class="change"><div class="ic">🏫</div><div>
        <div class="h">${esc(c.class_id)} PE indoors at ${clock(idx[c.period].start)}</div>
        <div class="d">No cleaner slot passes the rules today, so yoga & stretching in the hall instead.</div>
        ${ruleChips(plan, c.rules)}</div></div>`;
    }
    if (c.type === "venue") {
      const who = c.scope === "all" ? "Whole school" : `Classes ${c.scope.join(", ")}`;
      return `<div class="change"><div class="ic">${c.activity === "Assembly" ? "📣" : "🧩"}</div><div>
        <div class="h">${esc(c.activity)} indoors · ${esc(who)}</div>
        <div class="d">${esc(c.alternative[0])}. PM2.5 ${c.pm25} at ${clock(idx[c.period].start)}.</div>
        ${ruleChips(plan, c.rules)}</div></div>`;
    }
    return `<div class="change"><div class="ic">🫁</div><div>
      <div class="h">${esc(c.class_id)}: ${c.count} asthma-watch students stay in</div>
      <div class="d">During PE at ${clock(idx[c.period].start)} (PM2.5 ${c.pm25}): light indoor activity with a teacher.</div>
      ${ruleChips(plan, c.rules)}</div></div>`;
  }).join("");
}

function parentUrl() {
  const base = location.href.replace(/[^/]*$/, "");
  return `${base}parent.html?school=${SID}`;
}

function renderApprove(plan) {
  const n = plan.notices;
  $("brief").innerHTML = (n.principal_brief_en || []).map((b) => `<li>${esc(b)}</li>`).join("");
  const text = state.lang === "hi" ? n.parent_notice_hi : n.parent_notice_en;
  $("notice").textContent = text;
  $("langHi").setAttribute("aria-pressed", state.lang === "hi");
  $("langEn").setAttribute("aria-pressed", state.lang === "en");
  $("noticeSrc").textContent = n.source === "bedrock"
    ? "Written by the CleanHour agent (Strands Agents on Amazon Bedrock) from the plan's facts."
    : `Template notice${n.agent_error ? " · agent offline: " + n.agent_error.slice(0, 90) : ""}`;

  const status = state.item.status;
  const actions = $("actions");
  if (status === "pending_approval") {
    actions.innerHTML = `<button class="btn primary block" id="approveBtn" ${state.busy ? "disabled" : ""}>${state.busy ? '<span class="spin"></span> Publishing…' : "✓ Approve & publish"}</button>
      <p class="note">${plan.regulatory ? "Includes GRAP-required changes: these auto-apply at the deadline if you don't respond." : "Advisory changes: nothing goes to parents until you approve."}</p>`;
    $("approveBtn").addEventListener("click", approve);
  } else if (status === "published") {
    const share = `https://wa.me/?text=${encodeURIComponent(text + "\n\n" + parentUrl())}`;
    const audio = state.item.has_voice ? `<audio controls preload="none" src="${API}/api/public/${SID}/voice/${state.date}"></audio>` : `<p class="note">Hindi voice note (Amazon Polly) is generated on publish in the AWS deployment.</p>`;
    actions.innerHTML = `<a class="btn whatsapp block" href="${share}" target="_blank" rel="noopener">Share to class WhatsApp groups</a>
      ${audio}
      <a class="btn block" href="${parentUrl()}" target="_blank" rel="noopener">Open parent page ↗</a>
      <p class="note">Approved by ${esc(state.item.approved_by || "—")}.</p>`;
  } else {
    actions.innerHTML = `<p class="note">${esc(STATUS_TEXT[status] || status)}</p>`;
  }
}

async function ask(question) {
  if (!state.item || !state.item.plan) { toast("Run the check first."); return; }
  $("answer").innerHTML = '<span class="spin"></span>';
  try {
    const r = await api(`/api/schools/${SID}/plans/${state.date}/ask`, { method: "POST", body: { question } });
    $("answer").textContent = r.answer || r.error;
  } catch (e) { $("answer").textContent = e.message; }
  loadLog();
}

async function loadLog() {
  try {
    const log = await api(`/api/schools/${SID}/audit`);
    $("log").innerHTML = log.slice(0, 12).map((l) => `<li><div>${esc(l.detail || l.event)}</div><div class="at">${esc(l.event)} · ${new Date(l.at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}</div></li>`).join("") || '<li class="note">No activity yet.</li>';
  } catch (e) { /* ignore */ }
}

async function init() {
  $("viewBefore").addEventListener("click", () => { state.view = "before"; render(); });
  $("viewAfter").addEventListener("click", () => { state.view = "after"; render(); });
  $("langHi").addEventListener("click", () => { state.lang = "hi"; render(); });
  $("langEn").addEventListener("click", () => { state.lang = "en"; render(); });
  $("grap").addEventListener("change", (e) => setGrap(e.target.value));
  $("askForm").addEventListener("submit", (e) => { e.preventDefault(); const q = $("askInput").value.trim(); if (q) ask(q); });
  const suggestions = ["Can 7A do sports practice at 12:30?", "Kya 3A ke asthma wale bachche bahar khel sakte hain?", "Why is assembly indoors today?"];
  $("suggest").innerHTML = suggestions.map((s) => `<button type="button">${esc(s)}</button>`).join("");
  $("suggest").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { $("askInput").value = b.textContent; ask(b.textContent); }));
  $("parentLink").href = `parent.html?school=${SID}`;

  try {
    state.school = await api(`/api/schools/${SID}`);
    $("schoolName").textContent = state.school.name;
    $("grap").value = String(state.school.grap_stage);
  } catch (e) {
    $("schoolName").textContent = `Can't reach the CleanHour API (${e.message})`;
  }
  await selectDay(params.get("date") || istDate(0));
  loadLog();
}

init();
