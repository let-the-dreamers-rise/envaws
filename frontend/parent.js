const API = (window.CLEANHOUR_API || "").replace(/\/$/, "");
const params = new URLSearchParams(location.search);
const SID = params.get("school") || "demo-rohini";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const state = { lang: "hi", cls: localGet("cleanhour.class"), data: null };

function localGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
function localSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } }

const T = {
  hi: { today: "आज की हवा", worst: "सबसे खराब", at: "पर", pick: "आपके बच्चे की कक्षा", myday: "आज आपके बच्चे का दिन",
        notice: "स्कूल का संदेश", listen: "हिंदी में सुनें", none: "आज का अपडेट अभी तैयार हो रहा है। सुबह 6:45 तक देखें।",
        out: "बाहर", in: "अंदर", moved: "खेल का समय बदला", asthma: "अस्थमा सूची वाले बच्चे अंदर रहेंगे", assembly: "प्रार्थना सभा",
        recess: "रिसेस", pe: "खेल (पीटी)", indoorPE: "इनडोर पीटी (योग)", normal: "समय-सारणी सामान्य है", cleaner: "हवा साफ़",
        heat: "गर्मी", feels: "महसूस", cooler: "ठंडे समय पर" },
  en: { today: "Today's air", worst: "Worst", at: "at", pick: "Your child's class", myday: "Your child's day",
        notice: "Message from school", listen: "Listen in Hindi", none: "Today's update is being prepared. Check back by 6:45 AM.",
        out: "outdoors", in: "indoors", moved: "PE time changed", asthma: "Asthma-watch children stay indoors", assembly: "Assembly",
        recess: "Recess", pe: "PE", indoorPE: "Indoor PE (yoga)", normal: "Normal timetable", cleaner: "cleaner air",
        heat: "Heat", feels: "feels like", cooler: "cooler hour" },
};

function clock(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`;
}

function render() {
  const t = T[state.lang];
  $("hi").setAttribute("aria-pressed", state.lang === "hi");
  $("en").setAttribute("aria-pressed", state.lang === "en");
  const d = state.data;
  if (!d) return;
  const schoolName = state.lang === "hi" ? (d.school.name_hi || d.school.name) : d.school.name;
  if (!d.plan) {
    $("root").innerHTML = `<div class="card"><h2>${esc(schoolName)}</h2><p>${t.none}</p></div>`;
    return;
  }
  const p = d.plan, f = p.flag;
  const classes = Object.keys(p.timetable_after);
  if (!state.cls || !classes.includes(state.cls)) state.cls = classes[0];
  const dateText = new Date(d.date + "T00:00:00").toLocaleDateString(state.lang === "hi" ? "hi-IN" : "en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  $("root").innerHTML = `
    <div class="flagcard" style="background:${f.colour}">
      <div class="mid">${esc(schoolName)} · ${esc(dateText)}</div>
      <div class="big">${t.today}: ${esc(state.lang === "hi" ? f.hi : f.en)}</div>
      <div class="mid">${t.worst} PM2.5 ${f.pm25} ${t.at} ${clock(p.period_index[f.period].start)}</div>
      ${p.heat && p.heat.feels >= 35 ? `<div class="small">${t.heat}: ${t.feels} ${p.heat.feels} °C · ${clock(p.period_index[p.heat.period].start)}</div>` : ""}
      ${p.quiet ? `<div class="small">${t.normal}</div>` : ""}
    </div>
    <div class="card">
      <h2>${t.pick}</h2>
      <select id="cls">${classes.map((c) => `<option ${c === state.cls ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>
    </div>
    <div class="card"><h2>${t.myday}</h2><ul class="myday">${myDay(p, state.cls, t)}</ul></div>
    <div class="card">
      <h2>${t.notice}</h2>
      <div class="notice">${esc(state.lang === "hi" ? d.notices.parent_notice_hi : d.notices.parent_notice_en)}</div>
      ${d.has_voice ? `<h2 style="margin-top:14px">${t.listen}</h2><audio controls preload="none" src="${API}/api/public/${SID}/voice/${d.date}"></audio>` : ""}
    </div>`;
  $("cls").addEventListener("change", (e) => { state.cls = e.target.value; localSet("cleanhour.class", state.cls); render(); });
  $("foot").textContent = state.lang === "hi"
    ? "CleanHour हर सुबह हवा का पूर्वानुमान देखकर बच्चों का बाहर का समय साफ़ हवा वाले घंटे में रखता है। यह चिकित्सा सलाह नहीं है।"
    : "CleanHour checks the air forecast every morning and moves outdoor time to the cleanest hour. Not medical advice.";
}

function myDay(p, cid, t) {
  const venueIndoor = (act) => p.changes.some((c) => c.type === "venue" && c.activity === act && (c.scope === "all" || c.scope.includes(cid)));
  const asthma = p.changes.find((c) => c.type === "asthma" && c.class_id === cid);
  const items = [];
  for (const per of p.periods) {
    if (per.kind === "assembly" || per.kind === "recess") {
      const act = per.kind === "assembly" ? "Assembly" : "Recess";
      const indoor = venueIndoor(act);
      items.push([per.start, `${act === "Assembly" ? t.assembly : t.recess} · ${indoor ? t.in : t.out}`, indoor ? "indoor" : ""]);
      continue;
    }
    const cell = p.timetable_after[cid][per.id];
    if (cell.subject === "PE") {
      const move = p.changes.find((c) => c.type === "move" && c.class_id === cid);
      let text = `${t.pe} · ${t.out}`;
      if (move && move.driver === "heat") text += ` (${t.moved}, ${t.cooler}: ${clock(p.period_index[move.from].start)} → ${clock(per.start)}, ${move.feels_from} → ${move.feels_to} °C)`;
      else if (move) text += ` (${t.moved}: ${clock(p.period_index[move.from].start)} → ${clock(per.start)}, ${move.gain_pct}% ${t.cleaner})`;
      if (asthma) text += ` · ${t.asthma}`;
      items.push([per.start, text, move ? "moved" : ""]);
    } else if (cell.indoor_from) {
      items.push([per.start, t.indoorPE, "indoor"]);
    }
  }
  return items.map(([time, text, cls]) => `<li><span class="time">${clock(time)}</span><span class="what ${cls}">${esc(text)}</span></li>`).join("");
}

async function load() {
  try {
    const res = await fetch(`${API}/api/public/${SID}/latest${params.get("date") ? "?date=" + params.get("date") : ""}`);
    state.data = await res.json();
    if (!res.ok) throw new Error(state.data.error || res.statusText);
  } catch (e) {
    $("root").innerHTML = `<div class="card">Could not load: ${esc(e.message)}</div>`;
    return;
  }
  render();
}

$("hi").addEventListener("click", () => { state.lang = "hi"; render(); });
$("en").addEventListener("click", () => { state.lang = "en"; render(); });
load();
