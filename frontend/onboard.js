const API = (window.CLEANHOUR_API || "").replace(/\/$/, "");
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let image = null;

function toast(msg) {
  const t = $("toast"); t.textContent = msg; t.classList.remove("hidden");
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.add("hidden"), 4000);
}

// Shrink the photo in the browser: sharp enough to read, small enough for the API.
function shrink(file, maxSide = 1600) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * scale); c.height = Math.round(img.height * scale);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      resolve(c.toDataURL("image/jpeg", 0.85));
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

$("photo").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    image = await shrink(file);
    $("preview").src = image; $("preview").classList.remove("hidden");
    $("dropText").textContent = "Looks good. Tap to retake";
  } catch (err) { toast("Couldn't open that image."); }
});

$("locate").addEventListener("click", () => {
  if (!navigator.geolocation) return toast("Location isn't available in this browser.");
  navigator.geolocation.getCurrentPosition(
    (p) => { $("lat").value = p.coords.latitude.toFixed(4); $("lon").value = p.coords.longitude.toFixed(4); },
    () => toast("Couldn't get your location. Type it in instead."),
    { enableHighAccuracy: false, timeout: 8000 });
});

$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!image) return toast("Add a photo of the timetable first.");
  const btn = $("submit");
  btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Reading the timetable…';
  try {
    const res = await fetch(`${API}/api/schools`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ name: $("name").value, lat: $("lat").value, lon: $("lon").value,
        image_base64: image.split(",")[1], image_format: "jpeg" }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    showResult(data);
  } catch (err) {
    toast(err.message);
  } finally {
    btn.disabled = false; btn.textContent = "Read timetable & create school";
  }
});

function showResult(school) {
  const teaching = school.periods.filter((p) => p.kind === "teaching");
  const pe = school.classes.flatMap((c) => Object.entries(c.timetable).filter(([, v]) => v.subject === "PE").map(([pid]) => `${c.id} ${pid}`));
  $("result").classList.remove("hidden");
  $("result").innerHTML = `
    <h2>3 · ${esc(school.name)} is live</h2>
    <p>Found <b>${school.classes.length}</b> classes, <b>${teaching.length}</b> teaching periods
      (${esc(school.periods[0].start)}–${esc(school.periods[school.periods.length - 1].end)}) and <b>${pe.length}</b> outdoor PE periods${pe.length ? `: ${esc(pe.slice(0, 8).join(", "))}${pe.length > 8 ? "…" : ""}` : ""}.</p>
    <p class="note">From tomorrow, CleanHour plans this school at 5:30 AM. Check the timetable in the console and fix anything the photo got wrong.</p>
    <div class="actions" style="margin-top:12px">
      <a class="btn primary block" href="console.html?school=${encodeURIComponent(school.id)}">Open this school's console →</a>
      <a class="btn block" href="parent.html?school=${encodeURIComponent(school.id)}">Parent page link</a>
    </div>`;
  $("result").scrollIntoView({ behavior: "smooth" });
}
