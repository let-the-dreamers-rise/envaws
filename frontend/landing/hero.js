/* Hero: the transformation. PE tiles caught in morning smog lift out of it and glide to the
   clean midday periods while the inversion layer rises and the readout falls 184 → 90. */
(() => {
  const day = document.getElementById("day");
  if (!day) return;
  const CH = window.CH || {};
  const sky = day.querySelector(".day-sky");
  const track = day.querySelector(".track");
  const tiles = [...day.querySelectorAll(".tile")];
  const hazes = [...day.querySelectorAll(".haze")];
  const ceiling = day.querySelector(".ceiling");
  const sunline = day.querySelector(".sunline");
  const roTime = day.querySelector(".ro-time");
  const roNum = day.querySelector(".ro-num");
  const roBand = day.querySelector(".ro-band");

  // Period start (minutes since midnight) → period-average PM2.5, Rohini, 21 Nov 2025.
  const PERIODS = [[485, 184], [525, 170], [565, 153], [605, 135], [665, 109], [705, 97], [745, 92], [785, 90]];
  const BANDS = [[30, "Good", "#2e9e4f"], [60, "Satisfactory", "#8cc43f"], [90, "Moderate", "#c9a21a"],
    [120, "Poor", "#f08a24"], [250, "Very Poor", "#d93b3b"], [Infinity, "Severe", "#7e1f3c"]];
  const DAY_START = 465, DAY_LEN = 360; // 7:45 → 13:45
  const FROM = 0.056, TO = 0.889;

  const band = (pm) => BANDS.find((b) => Math.round(pm) <= b[0]);
  const clock = (m) => {
    const h = Math.floor(m / 60), mm = Math.round(m % 60);
    return `${((h + 11) % 12) + 1}:${String(mm).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`;
  };
  const pmAt = (m) => {
    if (m <= PERIODS[0][0]) return PERIODS[0][1];
    for (let i = 1; i < PERIODS.length; i++) {
      const [m0, v0] = PERIODS[i - 1], [m1, v1] = PERIODS[i];
      if (m <= m1) return v0 + ((v1 - v0) * (m - m0)) / (m1 - m0);
    }
    return PERIODS[PERIODS.length - 1][1];
  };

  const state = { t: 0 };
  let lastBand = "";
  const render = () => {
    const minutes = DAY_START + (FROM + (TO - FROM) * state.t) * DAY_LEN;
    const pm = pmAt(minutes);
    const b = band(pm);
    roTime.textContent = clock(Math.round(minutes / 5) * 5);
    roNum.textContent = Math.round(pm);
    if (b[1] !== lastBand) { roBand.textContent = b[1]; roBand.style.backgroundColor = b[2]; lastBand = b[1]; }
    const w = sky.clientWidth, h = sky.clientHeight;
    gsap.set(sunline, { x: (TO - FROM) * w * state.t });
    gsap.set(ceiling, { y: -h * 0.34 * state.t });
    hazes.forEach((el, i) => gsap.set(el, { yPercent: -38 * state.t * (1 + i * 0.25), opacity: 1 - 0.72 * state.t }));
    day.classList.toggle("is-clean", state.t > 0.7);
  };

  const motes = CH.motes ? CH.motes(day.querySelector(".motes"), { count: 80, colour: "232,196,160", density: () => 1 - state.t * 0.85 }) : null;

  const finalState = () => {
    state.t = 1;
    if (window.gsap) {
      render();
      tiles.forEach((el) => gsap.set(el, { x: (el.dataset.to - el.dataset.from) * track.clientWidth }));
    }
  };

  if (!CH.hasGsap) return;
  gsap.set(tiles, { xPercent: -50, x: 0 });
  if (CH.reduce) {
    finalState();
    addEventListener("resize", finalState);
    return;
  }

  const dx = (i, el) => (el.dataset.to - el.dataset.from) * track.clientWidth;
  const tl = gsap.timeline({ repeat: -1, repeatDelay: 0.6, defaults: { ease: "power3.inOut" }, paused: true })
    .set(state, { t: 0, onComplete: render })
    .set(tiles, { x: 0, y: 0, opacity: 1 })
    .to({}, { duration: 1.6 })
    .addLabel("lift")
    .to(state, { t: 1, duration: 3.4, onUpdate: render }, "lift")
    .to(tiles, { y: -14, duration: 0.9, stagger: 0.18, ease: "power3.out" }, "lift+=0.3")
    .to(tiles, { x: dx, duration: 2.4, stagger: 0.18 }, "lift+=0.6")
    .to(tiles, { y: 0, duration: 1, stagger: 0.18, ease: "power3.out" }, "lift+=2.2")
    .to({}, { duration: 2.4 })
    .to(tiles, { opacity: 0, duration: 0.6, ease: "power3.in" })
    .to(state, { t: 0, duration: 0.9, onUpdate: render }, "<");

  addEventListener("resize", () => tl.invalidate());
  CH.onScreen(day, (on) => (on ? tl.play() : tl.pause()), "0px");
  render();

  // Cursor-reactive depth: the haze layers sit at different heights in the air column.
  const hero = document.querySelector(".hero");
  if (matchMedia("(pointer: fine)").matches) {
    const movers = hazes.map((el) => ({ el, depth: +el.dataset.depth, x: gsap.quickTo(el, "x", { duration: 1.2 }), y: gsap.quickTo(el, "y", { duration: 1.2 }) }));
    const tileX = tiles.map((el) => gsap.quickTo(el, "rotation", { duration: 1.2 }));
    hero.addEventListener("pointermove", (e) => {
      const r = hero.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5, py = (e.clientY - r.top) / r.height - 0.5;
      movers.forEach((m) => { m.x(px * m.depth); m.y(py * m.depth * 0.6); });
      tileX.forEach((f, i) => f(px * (2 + i)));
    });
    hero.addEventListener("pointerleave", () => { movers.forEach((m) => { m.x(0); m.y(0); }); tileX.forEach((f) => f(0)); });
  }
})();
