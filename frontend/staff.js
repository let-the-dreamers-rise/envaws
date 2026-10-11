/* Staff changes: who teaches what, when, after CleanHour's plan. A PE teacher whose period moved,
   or a Maths teacher whose lesson swapped, needs to know before the first bell. */
window.CHStaff = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const clock = (hhmm) => {
    const [h, m] = hhmm.split(":").map(Number);
    return `${((h + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`;
  };

  function changesByTeacher(plan) {
    const idx = plan.period_index, out = {};
    const add = (teacher, text, moved) => (out[teacher] = out[teacher] || []).push({ text, moved });
    for (const [cid, row] of Object.entries(plan.timetable_after)) {
      for (const [pid, cell] of Object.entries(row)) {
        if (cell.indoor_from) add(cell.teacher, `${cid} PE stays at ${clock(idx[pid].start)} but moves indoors (yoga & stretching in the hall)`, true);
        else if (cell.moved_from) add(cell.teacher, `${cid} ${cell.subject}: now ${clock(idx[pid].start)} (was ${clock(idx[cell.moved_from].start)})`, true);
      }
    }
    for (const c of plan.changes.filter((x) => x.type === "asthma")) {
      const t = plan.timetable_after[c.class_id][c.period].teacher;
      add(t, `${c.count} asthma-watch students in ${c.class_id} stay in during PE at ${clock(idx[c.period].start)}. Arrange supervised indoor activity`, false);
    }
    return out;
  }

  function allStaffLines(plan) {
    return plan.changes.filter((c) => c.type === "venue").map((c) =>
      `${c.alternative[0]}${c.scope === "all" ? "" : ` (classes ${c.scope.join(", ")})`}, ${clock(plan.period_index[c.period].start)}`);
  }

  function shareText(plan, byTeacher) {
    const lines = [`CleanHour staff changes · ${plan.date}`];
    allStaffLines(plan).forEach((l) => lines.push(`• All staff: ${l}`));
    for (const [t, items] of Object.entries(byTeacher)) items.forEach((i) => lines.push(`• ${t}: ${i.text}`));
    return lines.join("\n");
  }

  function render(container, plan, me) {
    const byTeacher = changesByTeacher(plan);
    const teachers = Object.keys(byTeacher).sort();
    const mine = me && me.role === "teacher" ? me.name : null;
    if (mine && byTeacher[mine]) teachers.splice(teachers.indexOf(mine), 1), teachers.unshift(mine);
    if (!teachers.length && !allStaffLines(plan).length) {
      container.innerHTML = '<p class="note">No staff changes today.</p>';
      return;
    }
    const block = (t) => `<div class="staff ${t === mine ? "staff-mine" : ""}">
      <div class="h">${t === mine ? `Your day, ${esc(t)}` : esc(t)}</div>
      <ul>${byTeacher[t].map((i) => `<li class="${i.moved ? "moved" : ""}">${esc(i.text)}</li>`).join("")}</ul></div>`;
    const share = `https://wa.me/?text=${encodeURIComponent(shareText(plan, byTeacher))}`;
    container.innerHTML = `
      ${allStaffLines(plan).map((l) => `<p class="note" style="margin:0 0 6px">All staff: ${esc(l)}</p>`).join("")}
      ${teachers.map(block).join("")}
      <a class="btn block" style="margin-top:10px" href="${share}" target="_blank" rel="noopener">Share with the staff group</a>`;
  }

  return { render, changesByTeacher };
})();
