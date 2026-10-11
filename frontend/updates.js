/* Mid-day re-checks: CleanHour may tighten the rest of a published day on its own (outdoor -> indoor)
   when the forecast worsens or GRAP is raised, but it never loosens without a newly approved plan. */
window.CHUpdates = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const REPLAY_TIME = "11:00"; // replays simulate a late-morning re-check

  function banner(updates, lang = "en") {
    const hi = lang === "hi";
    return (updates || []).map((u) => `<div class="update" role="status">
      <b>${hi ? "अपडेट" : "Update"} ${esc(u.at)}</b> · ${esc(hi && u.summary_hi ? u.summary_hi : u.summary)}${hi ? "।" : "."}<br>
      <span class="note">${esc((hi && u.why_hi ? u.why_hi : u.why).join(" "))}</span></div>`).join("");
  }

  async function run(ctx, reason) {
    const body = ctx.item.plan.mode === "replay" ? { at: REPLAY_TIME } : {};
    const r = await ctx.api(`/api/schools/${ctx.sid}/plans/${ctx.date}/recheck`, { method: "POST", body });
    ctx.toast(r.tightened && r.tightened.length
      ? `${reason}Re-check at ${r.at}: ${r.tightened.length} PE period(s) moved indoors. Parents and staff can see it now.`
      : `${reason}Re-check at ${r.at}: the rest of the day is still safe.`, 5000);
    await ctx.after();
  }

  // Console card: shows updates and, for staff who may re-run plans, a manual re-check button.
  function render(card, ctx) {
    const plan = ctx.item && ctx.item.plan;
    const published = ctx.item && ctx.item.status === "published";
    card.classList.toggle("hidden", !published);
    if (!published) return;
    const replay = plan.mode === "replay";
    card.innerHTML = `<h2>During the day</h2>
      ${banner(plan.updates) || '<p class="note">Re-checked at 9:30 and 11:30 against the latest forecast and GRAP stage. CleanHour can make the rest of the day safer on its own, never riskier.</p>'}
      ${ctx.can("RunPlan") ? `<button class="btn block" id="recheckBtn" type="button">Run the ${replay ? "11:00 (simulated)" : "mid-day"} re-check now</button>` : ""}`;
    const btn = card.querySelector("#recheckBtn");
    if (btn) btn.addEventListener("click", async () => {
      btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Re-checking…';
      try { await run(ctx, ""); } catch (e) { ctx.toast(e.message); btn.disabled = false; }
    });
  }

  return { render, run, banner };
})();
