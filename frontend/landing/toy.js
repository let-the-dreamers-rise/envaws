/* Playground: drag the sun across the real school day; the haze follows the real PM2.5 curve and
   the verdicts use the same thresholds as backend/cleanhour/policies.cedar. */
(() => {
  const input = document.getElementById("toyTime");
  if (!input) return;
  const CH = window.CH || {};
  const sky = document.getElementById("toySky");
  const haze = document.getElementById("toyHaze");
  const sun = document.getElementById("toySun");
  const out = { clock: document.getElementById("toyClock"), pm: document.getElementById("toyPm"), band: document.getElementById("toyBand"), list: document.getElementById("toyVerdicts") };

  // Hourly PM2.5 measured at the CPCB Rohini DPCC station, Delhi, 6 Nov 2025.
  const HOURS = [[360, 522], [420, 505], [480, 486], [540, 429], [600, 324], [660, 189], [720, 94], [780, 85], [840, 72], [900, 64], [960, 61]];
  const MIN = 420, MAX = 900;
  const BANDS = [[30, "Good"], [60, "Satisfactory"], [90, "Moderate"], [120, "Poor"], [250, "Very Poor"], [Infinity, "Severe"]];
  const RULES = [
    [(c) => c.grap >= 4, "GRAP Stage IV: no outdoor activity"],
    [(c) => c.grap >= 3 && c.exertion === "high", "GRAP Stage III: outdoor sports suspended"],
    [(c) => c.pm > 250, "Severe air: everyone stays in"],
    [(c) => c.pm > 120 && c.exertion !== "low", "Very Poor air: no outdoor exertion"],
    [(c) => c.primary && c.pm > 120, "Very Poor air: classes 1–5 stay in"],
    [(c) => c.kind === "assembly" && c.pm > 90, "Poor air: assembly moves indoors"],
    [(c) => c.asthma && c.pm > 90, "Poor air: asthma-watch kids stay in"],
  ];
  const WHO = [
    { label: "PE · Class 7", exertion: "high", kind: "pe" },
    { label: "PE · Class 3", exertion: "high", kind: "pe", primary: true },
    { label: "Asthma-watch kids", exertion: "high", kind: "pe", asthma: true },
    { label: "Assembly", exertion: "low", kind: "assembly" },
  ];

  const pmAt = (m) => {
    for (let i = 1; i < HOURS.length; i++) {
      const [m0, v0] = HOURS[i - 1], [m1, v1] = HOURS[i];
      if (m <= m1) return v0 + ((v1 - v0) * (m - m0)) / (m1 - m0);
    }
    return HOURS[HOURS.length - 1][1];
  };
  const clock = (m) => { const h = Math.floor(m / 60); return `${((h + 11) % 12) + 1}:${String(m % 60).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`; };
  const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  // The curve: PM2.5 drawn as the height of the smog across the day.
  const path = document.getElementById("curvePath");
  let d = "M0,200";
  for (let m = MIN; m <= MAX; m += 10) d += ` L${(((m - MIN) / (MAX - MIN)) * 600).toFixed(1)},${(200 - (pmAt(m) / 560) * 200).toFixed(1)}`;
  path.setAttribute("d", d + " L600,200 Z");

  const grapValue = () => +document.querySelector('input[name="grap"]:checked').value;
  const animate = CH.hasGsap && !CH.reduce;
  const sunX = animate ? gsap.quickTo(sun, "x", { duration: 0.6, ease: "power3.out" }) : null;
  const sunY = animate ? gsap.quickTo(sun, "y", { duration: 0.6, ease: "power3.out" }) : null;

  const render = () => {
    const m = +input.value;
    const pm = Math.round(pmAt(m));
    const smog = Math.min(1, pm / 220);
    const p = (m - MIN) / (MAX - MIN);
    out.clock.textContent = clock(m);
    out.pm.textContent = pm;
    out.band.textContent = BANDS.find((b) => pm <= b[0])[1];
    input.setAttribute("aria-valuetext", `${clock(m)}, PM2.5 ${pm}`);

    const x = p * sky.clientWidth;
    const y = sky.clientHeight * (0.82 - Math.sin(Math.PI * p) * 0.62);
    if (animate) {
      sunX(x); sunY(y);
      gsap.to(haze, { scaleY: 0.25 + 0.75 * smog, opacity: 0.2 + 0.8 * smog, duration: 0.9, ease: "power3.out", overwrite: true });
    } else {
      sun.style.transform = `translate(${x}px, ${y}px)`;
      haze.style.transform = `scaleY(${0.25 + 0.75 * smog})`;
      haze.style.opacity = 0.2 + 0.8 * smog;
    }

    const grap = grapValue();
    out.list.innerHTML = WHO.map((w) => {
      const blocked = RULES.filter(([test]) => test({ ...w, pm, grap })).map(([, why]) => why);
      const ok = blocked.length === 0;
      return `<li class="${ok ? "ok" : "no"}"><b>${esc(w.label)}: ${ok ? "outdoors" : "indoors"}</b><small>${esc(ok ? "No rule blocks it at this minute" : blocked[0])}</small></li>`;
    }).join("");
  };

  input.addEventListener("input", render);
  document.querySelectorAll('input[name="grap"]').forEach((r) => r.addEventListener("change", render));
  addEventListener("resize", render);
  render();
})();
