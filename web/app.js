import { HABITABLE_AU, norm, orbit, sub } from "./sim.js";
import { DIRECTIONS, Universe } from "./tools.js";

const COLOURS = { Sun: "#f5c542", Mercury: "#9a9a9a", Venus: "#d9b38c", Earth: "#4f8fe8", Mars: "#d0603a",
  Jupiter: "#c99b6d", Saturn: "#e2cf8f", Uranus: "#8fd6d9", Neptune: "#4a6fd6" };
const colour = (name) => COLOURS[name] || "#ff4fd8";
// Names can come from a shared plan, so they are escaped before going into HTML.
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

const sky = document.getElementById("sky");
const g = sky.getContext("2d");
let universe = new Universe();
const view = { extent: 40 }; // AU at the edge of the view, before the square-root squeeze
const clock = { playing: true, yearsPerSecond: 2, years: 0, last: 0 };
const trails = new Map(); // name -> recent positions
const TRAIL = 240;
let selected = "Earth";

function fit() {
  const r = sky.getBoundingClientRect();
  sky.width = r.width * devicePixelRatio;
  sky.height = r.height * devicePixelRatio;
}

// Square-root scale, so Mercury and Neptune fit on one screen. Centred on the Sun, or what replaced it.
function toScreen(pos, centre) {
  const half = Math.min(sky.width, sky.height) / 2 - 20 * devicePixelRatio;
  const x = pos[0] - centre[0], y = pos[1] - centre[1];
  const r = Math.hypot(x, y);
  const s = r ? (Math.sqrt(r / view.extent) * half) / r : 0;
  return [sky.width / 2 + x * s, sky.height / 2 - y * s];
}

function draw() {
  g.fillStyle = "#000";
  g.fillRect(0, 0, sky.width, sky.height);
  const centre = universe.anchor().pos;
  g.font = `${12 * devicePixelRatio}px "IBM Plex Mono", monospace`;
  g.lineWidth = devicePixelRatio;
  for (const [name, points] of trails) {
    g.strokeStyle = colour(name) + "66";
    g.beginPath();
    points.forEach((p, k) => {
      const [x, y] = toScreen(p, centre);
      k ? g.lineTo(x, y) : g.moveTo(x, y);
    });
    g.stroke();
  }
  for (const b of universe.bodies) {
    const [x, y] = toScreen(b.pos, centre);
    g.fillStyle = colour(b.name);
    g.beginPath();
    g.arc(x, y, (b.name === "Sun" ? 7 : 4) * devicePixelRatio, 0, 2 * Math.PI);
    g.fill();
    if (b.name === selected) {
      g.strokeStyle = "#e8b04a";
      g.beginPath();
      g.arc(x, y, 10 * devicePixelRatio, 0, 2 * Math.PI);
      g.stroke();
    }
    g.fillStyle = "#8a8f97";
    g.fillText(b.name, x + 8 * devicePixelRatio, y - 8 * devicePixelRatio);
  }
}

function remember() {
  const names = new Set(universe.bodies.map((b) => b.name));
  for (const b of universe.bodies) {
    const t = trails.get(b.name) || [];
    t.push([...b.pos]);
    if (t.length > TRAIL) t.shift();
    trails.set(b.name, t);
  }
  for (const name of trails.keys()) if (!names.has(name)) trails.delete(name);
}

// Steps of a plan still to come. Runs in it play out in real time.
let queue = [];

function next() {
  while (queue.length) {
    const { tool, args } = queue.shift();
    try {
      if (universe.call(tool, args) && tool === "run") return;
    } catch (e) {
      $("error").textContent = `${tool}: ${e.message}`;
      queue = [];
    }
  }
}

// With no plan running, play drives an open-ended run. Changing anything
// ends it, and the next frame starts a new one, as a plan would.
function current() {
  if (!universe.current) {
    universe.current = universe.run({ years: 5000 });
    universe.current.live = true;
  }
  return universe.current;
}

function load(plan) {
  universe = new Universe();
  trails.clear();
  Object.assign(earthRange, { lo: Infinity, hi: 0 });
  clock.years = 0;
  $("error").textContent = $("arrives").textContent = "";
  queue = [...plan];
  next();
  table();
}

function frame(now) {
  const dt = Math.min((now - clock.last) / 1000, 0.1);
  clock.last = now;
  if (clock.playing) {
    const run = current();
    const before = run.t;
    run.advance(dt * clock.yearsPerSecond * 365.25);
    clock.years += (run.t - before) / 365.25;
    remember();
    status();
    if (run.done) {
      closeRun();
      next();
    }
  }
  draw();
  $("year").textContent = `year ${clock.years.toFixed(1)}`;
  requestAnimationFrame(frame);
}

const $ = (id) => document.getElementById(id);

function table() {
  const sun = universe.bodies.find((b) => b.name === "Sun");
  $("bodies").tBodies[0].innerHTML = universe.bodies.map((b) => {
    const o = orbit(universe.bodies, b);
    const from = sun && b !== sun ? norm(sub(b.pos, sun.pos)).toFixed(3) : "";
    const a = o.bound ? o.a_au.toFixed(3) : o.orbits ? "unbound" : "";
    return `<tr data-name="${esc(b.name)}"${b.name === selected ? ' class="picked"' : ""}><td><span class="swatch" style="background:${colour(b.name)}"></span>${esc(b.name)}</td>`
      + `<td class="num">${from}</td><td class="num${o.orbits && !o.bound ? " unbound" : ""}">${a}</td>`
      + `<td class="num">${o.orbits ? o.e.toFixed(3) : ""}</td></tr>`;
  }).join("");
}
setInterval(table, 250);

// Earth's closest and farthest from the Sun over every run so far.
const earthRange = { lo: Infinity, hi: 0 };
function status() {
  const run = universe.current;
  if (run && run.closest.Earth !== undefined) {
    earthRange.lo = Math.min(earthRange.lo, run.closest.Earth);
    earthRange.hi = Math.max(earthRange.hi, run.farthest.Earth);
  }
  const alive = universe.bodies.some((b) => b.name === "Earth");
  const events = [...universe.events, ...(run ? run.events : [])];
  if (!alive) $("earth").textContent = "Earth is gone.";
  else if (earthRange.hi) {
    const ok = earthRange.lo >= HABITABLE_AU[0] && earthRange.hi <= HABITABLE_AU[1];
    $("earth").textContent = `Earth ${earthRange.lo.toFixed(3)} to ${earthRange.hi.toFixed(3)} AU from the Sun, `
      + (ok ? "inside" : "outside") + " the habitable zone";
  }
  $("earth").classList.toggle("unbound", alive && !(earthRange.lo >= HABITABLE_AU[0] && earthRange.hi <= HABITABLE_AU[1]));
  if ($("events").children.length !== events.length) {
    $("events").innerHTML = events.map((e) => `<li>${esc(e)}</li>`).join("");
  }
}
setInterval(status, 250);

// Ends the run in progress, logging how long it went, so the log stays a plan that replays.
// A plan's run cut short is logged as the part that ran.
function closeRun() {
  const run = universe.current;
  if (run && run.t > 0) {
    const years = run.t / 365.25;
    if (run.live) universe.log.push({ tool: "run", args: { years } });
    else if (!run.done) universe.log.findLast((s) => s.tool === "run").args = { years };
    universe.events.push(...run.events);
  } else if (run && !run.live) {
    universe.log.pop();
  }
  if (run && !run.done) queue = [];
  universe.current = null;
}

$("reset").onclick = () => {
  $("preset").value = "";
  $("question").textContent = "";
  load([]);
};

$("preset").onchange = async (e) => {
  if (!e.target.value) return;
  openPlan(await (await fetch(`plans/${e.target.value}.json`)).json());
};

// A plan.json saved by the command line: {"question": ..., "plan": [...]}.
function openPlan(saved) {
  if (!Array.isArray(saved.plan)) throw new Error("that file has no plan in it");
  load(saved.plan);
  $("question").textContent = saved.question || "";
}

$("planfile").onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    openPlan(JSON.parse(await file.text()));
  } catch (err) {
    $("error").textContent = `Couldn't read ${file.name}: ${err.message}`;
  }
};

// Everything done so far as a plan, the run in progress included.
function planSoFar() {
  const plan = universe.log.map((s) => ({ tool: s.tool, args: { ...s.args } }));
  const run = universe.current;
  if (run && run.t > 0 && run.live) plan.push({ tool: "run", args: { years: run.t / 365.25 } });
  else if (run && !run.live) plan.findLast((s) => s.tool === "run").args.years = run.t / 365.25;
  return plan;
}

// The plan goes in the URL fragment, base64 JSON, so the link replays it anywhere.
const encode = (saved) => btoa(unescape(encodeURIComponent(JSON.stringify(saved))));
const decode = (text) => JSON.parse(decodeURIComponent(escape(atob(text))));

$("share").onclick = async () => {
  const saved = { question: $("question").textContent || "Something I did to the solar system", plan: planSoFar() };
  const url = `${location.origin}${location.pathname}#plan=${encode(saved)}`;
  history.replaceState(null, "", url);
  try {
    await navigator.clipboard.writeText(url);
    $("share").textContent = "Copied";
  } catch {
    $("share").textContent = "Link is in the address bar";
  }
  setTimeout(() => { $("share").textContent = "Copy link"; }, 2000);
};

if (location.hash.startsWith("#plan=")) {
  try {
    openPlan(decode(location.hash.slice(6)));
  } catch (err) {
    $("error").textContent = `That link's plan couldn't be read: ${err.message}`;
  }
}

function act(tool, args) {
  closeRun();
  try {
    universe.call(tool, args);
    $("error").textContent = "";
  } catch (e) {
    universe.log.pop();
    $("error").textContent = e.message;
  }
  table();
}

for (const sel of document.querySelectorAll(".dirs")) {
  sel.innerHTML = DIRECTIONS.map((d) => `<option>${d}</option>`).join("");
}
$("remove").onclick = () => act("remove_body", { name: selected });
// Number inputs become numbers; everything else, a name like "2031" included, stays text.
const fields = (form) => Object.fromEntries([...form.elements].filter((el) => el.name)
  .map((el) => [el.name, el.type === "number" ? +el.value : el.value]));
for (const [id, tool, key] of [["scale", "scale_mass", "name"], ["kick", "kick", "name"], ["smash", "smash", "target"]]) {
  $(id).onsubmit = (e) => {
    e.preventDefault();
    act(tool, { [key]: selected, ...fields(e.target) });
  };
}

$("flyby").onsubmit = (e) => {
  e.preventDefault();
  closeRun();
  try {
    const out = universe.call("add_flyby", fields(e.target));
    $("arrives").textContent = `closest in ${out.closest_approach_in_years} years`;
    $("error").textContent = "";
  } catch (err) {
    universe.log.pop();
    $("error").textContent = err.message;
  }
  table();
};

function pick(name) {
  selected = name;
  table();
  for (const el of document.querySelectorAll(".needs-body")) el.textContent = name;
}
$("bodies").onclick = (e) => {
  const row = e.target.closest("tr[data-name]");
  if (row) pick(row.dataset.name);
};
// A click on the sky picks the nearest body within 20 pixels.
sky.onclick = (e) => {
  const r = sky.getBoundingClientRect();
  const px = (e.clientX - r.left) * devicePixelRatio, py = (e.clientY - r.top) * devicePixelRatio;
  const centre = universe.anchor().pos;
  let best = null, bestD = 20 * devicePixelRatio;
  for (const b of universe.bodies) {
    const [x, y] = toScreen(b.pos, centre);
    const d = Math.hypot(x - px, y - py);
    if (d < bestD) [best, bestD] = [b.name, d];
  }
  if (best) pick(best);
};
$("play").onclick = () => {
  clock.playing = !clock.playing;
  $("play").textContent = clock.playing ? "Pause" : "Play";
};
$("speed").onchange = (e) => { clock.yearsPerSecond = +e.target.value; };

addEventListener("resize", () => { fit(); draw(); });
fit();
requestAnimationFrame((now) => { clock.last = now; frame(now); });
