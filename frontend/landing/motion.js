/* Shared motion: buoyant reveals, count-ups, offscreen pausing, particle motes.
   Physics: things rise and decelerate like warm air (power3.out); nothing snaps or bounces. */
(() => {
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const hasGsap = !!(window.gsap && window.ScrollTrigger && window.SplitText);
  const CH = (window.CH = { reduce, hasGsap });
  if (!hasGsap) root.classList.add("no-gsap");

  const nav = document.getElementById("nav");
  const onScroll = () => nav && nav.classList.toggle("is-scrolled", scrollY > 40);
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Pause looping work when it is offscreen.
  const onScreen = (el, cb, margin = "80px") => {
    const io = new IntersectionObserver((entries) => entries.forEach((e) => cb(e.isIntersecting)), { rootMargin: margin });
    io.observe(el);
  };
  CH.onScreen = onScreen;
  document.querySelectorAll(".loop").forEach((el) => onScreen(el, (on) => el.classList.toggle("is-on", on && !reduce)));
  const marquee = document.querySelector(".marquee");
  if (marquee) onScreen(marquee, (on) => marquee.classList.toggle("is-off", !on));

  // Particle motes on a canvas. density(): 0..1, how much smog is in the air right now.
  CH.motes = (canvas, { count = 70, colour = "244,239,230", rise = 0.12, density = () => 1 } = {}) => {
    const ctx = canvas.getContext("2d");
    let w = 0, h = 0, raf = 0, running = false;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const pts = Array.from({ length: count }, () => ({ x: Math.random(), y: Math.random(), r: 0.6 + Math.random() * 1.8, s: 0.4 + Math.random(), p: Math.random() * 6.28 }));
    const size = () => {
      w = canvas.clientWidth; h = canvas.clientHeight;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const draw = (time) => {
      const d = density();
      ctx.clearRect(0, 0, w, h);
      const visible = Math.round(count * (0.15 + 0.85 * d));
      for (let i = 0; i < count; i++) {
        const q = pts[i];
        q.y -= (rise * q.s * (1.4 - d)) / 100;
        q.x += Math.sin(time / 2400 + q.p) * 0.0004;
        if (q.y < -0.05) { q.y = 1.05; q.x = Math.random(); }
        if (i >= visible) continue;
        ctx.globalAlpha = 0.25 + 0.5 * d * (q.r / 2.4);
        ctx.beginPath();
        ctx.arc(q.x * w, q.y * h * (0.45 + 0.55 * d) + h * 0.55 * (1 - d), q.r, 0, 6.283);
        ctx.fillStyle = `rgb(${colour})`;
        ctx.fill();
      }
      if (running) raf = requestAnimationFrame(draw);
    };
    const start = () => { if (running || reduce) return; running = true; raf = requestAnimationFrame(draw); };
    const stop = () => { running = false; cancelAnimationFrame(raf); };
    size();
    new ResizeObserver(size).observe(canvas);
    onScreen(canvas, (on) => (on ? start() : stop()));
    if (reduce) draw(0);
    return { start, stop };
  };

  const footerMotes = document.querySelector(".footer-motes");
  if (footerMotes) CH.motes(footerMotes, { count: 36, colour: "11,13,18", rise: 0.06, density: () => 0.3 });

  const countUps = () => {
    document.querySelectorAll("[data-count]").forEach((el) => {
      const target = parseFloat(el.dataset.count);
      const decimals = parseInt(el.dataset.decimals || "0", 10);
      if (!hasGsap || reduce || target === 0) return;
      const obj = { v: 0 };
      el.textContent = (0).toFixed(decimals);
      gsap.to(obj, {
        v: target, duration: 1.8, ease: "power3.out",
        scrollTrigger: { trigger: el, start: "top 88%", once: true },
        onUpdate: () => { el.textContent = obj.v.toFixed(decimals); },
      });
    });
  };

  if (!hasGsap || reduce) return;
  gsap.registerPlugin(ScrollTrigger, SplitText);
  gsap.defaults({ ease: "power3.out", duration: 0.9 });
  gsap.set("[data-rise]", { autoAlpha: 0, y: 36 });
  gsap.set("[data-split]", { visibility: "hidden" });

  // Staggered entrances: content rises into place as it scrolls in.
  ScrollTrigger.batch("[data-rise]", {
    start: "top 90%", once: true,
    onEnter: (batch) => gsap.to(batch, { autoAlpha: 1, y: 0, duration: 1.1, stagger: 0.12, overwrite: true }),
  });

  // Masked line reveals on every headline: lines rise out of their own mask.
  document.fonts.ready.then(() => {
    document.querySelectorAll("[data-split]").forEach((el) => {
      const inHero = !!el.closest(".hero");
      SplitText.create(el, {
        type: "lines", mask: "lines", autoSplit: true,
        onSplit(self) {
          gsap.set(el, { visibility: "visible" });
          return gsap.from(self.lines, {
            yPercent: 110, duration: 1.2, stagger: 0.13, delay: inHero ? 0.15 : 0,
            scrollTrigger: inHero ? undefined : { trigger: el, start: "top 86%", once: true },
          });
        },
      });
    });
    ScrollTrigger.refresh();
  });

  countUps();

  // Closing: the last of the haze sinks away as the sky clears.
  gsap.fromTo(".closing-haze", { yPercent: -15, opacity: 1 }, {
    yPercent: 45, opacity: 0.15, ease: "none",
    scrollTrigger: { trigger: ".closing", start: "top bottom", end: "bottom bottom", scrub: true },
  });
})();
