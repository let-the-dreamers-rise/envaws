/* Scroll-driven sections: the before/after scrub and the pinned 5:30 → 6:45 AM stage. */
(() => {
  const CH = window.CH || {};
  const steps = [...document.querySelectorAll(".step")];
  const cards = [...document.querySelectorAll(".stage-card")];
  const clockEl = document.getElementById("clockTime");
  const fill = document.getElementById("progressFill");

  const activate = (i) => {
    steps.forEach((s, j) => s.classList.toggle("is-active", j === i));
    cards.forEach((c, j) => c.classList.toggle("is-active", j === i));
  };
  const clock = (m) => `${Math.floor(m / 60)}:${String(Math.round(m % 60)).padStart(2, "0")}`;

  if (!CH.hasGsap) {
    // Without GSAP, an observer still walks the stage through the steps.
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) activate(steps.indexOf(e.target));
    }), { rootMargin: "-45% 0px -45% 0px" });
    steps.forEach((s) => io.observe(s));
    return;
  }

  // Pinned stage: the active step drives the stage card; the clock and progress scrub with scroll.
  steps.forEach((step, i) => {
    ScrollTrigger.create({
      trigger: step, start: "top 60%", end: "bottom 60%",
      onToggle: (self) => self.isActive && activate(i),
    });
  });
  activate(0);
  gsap.to(fill, {
    scaleX: 1, ease: "none",
    scrollTrigger: {
      trigger: ".story-steps ol", start: "top 60%", end: "bottom 60%", scrub: CH.reduce ? false : 0.6,
      onUpdate: (self) => { clockEl.textContent = clock(330 + 75 * self.progress); },
    },
  });

  // Before/after: the PE tile travels across the day as you scroll; PM2.5 scrubs with it.
  const tile = document.getElementById("scrubTile");
  const lane = document.getElementById("scrubDay");
  const timeEl = document.getElementById("scrubTime");
  const pmEl = document.getElementById("scrubPm");
  const PERIODS = [[485, 184], [525, 170], [565, 153], [605, 135], [665, 109], [705, 97], [745, 92], [785, 90]];
  const pmAt = (m) => {
    for (let i = 1; i < PERIODS.length; i++) {
      const [m0, v0] = PERIODS[i - 1], [m1, v1] = PERIODS[i];
      if (m <= m1) return v0 + ((v1 - v0) * (m - m0)) / (m1 - m0);
    }
    return 90;
  };
  const shortClock = (m) => { const h = Math.floor(m / 60); return `${((h + 11) % 12) + 1}:${String(Math.round(m % 60)).padStart(2, "0")}`; };
  const update = (p) => {
    const minutes = 485 + 300 * p;
    timeEl.textContent = shortClock(Math.round(minutes / 5) * 5);
    pmEl.textContent = Math.round(pmAt(minutes));
    gsap.set(tile, { x: p * Math.max(0, lane.clientWidth - tile.offsetWidth - 20) });
  };
  if (CH.reduce) { update(1); addEventListener("resize", () => update(1)); return; }
  ScrollTrigger.create({
    trigger: "#compare", start: "top 65%", end: "bottom 55%", scrub: 0.8,
    onUpdate: (self) => update(self.progress),
    onRefresh: (self) => update(self.progress),
  });
})();
