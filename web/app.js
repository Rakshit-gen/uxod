import { Universe } from "./tools.js";

const COLOURS = { Sun: "#f5c542", Mercury: "#9a9a9a", Venus: "#d9b38c", Earth: "#4f8fe8", Mars: "#d0603a",
  Jupiter: "#c99b6d", Saturn: "#e2cf8f", Uranus: "#8fd6d9", Neptune: "#4a6fd6" };
const colour = (name) => COLOURS[name] || "#ff4fd8";

const sky = document.getElementById("sky");
const g = sky.getContext("2d");
let universe = new Universe();
const view = { extent: 40 }; // AU at the edge of the view, before the square-root squeeze
const clock = { playing: true, yearsPerSecond: 2, years: 0, last: 0 };
const trails = new Map(); // name -> recent positions
const TRAIL = 240;

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

// The open-ended run that the play button drives. Changing anything ends it
// and the next frame starts a new one, as a plan would.
function live() {
  if (!universe.current || universe.current.done) universe.current = universe.run({ years: 5000 });
  return universe.current;
}

function frame(now) {
  const dt = Math.min((now - clock.last) / 1000, 0.1);
  clock.last = now;
  if (clock.playing) {
    const run = live();
    const before = run.t;
    run.advance(dt * clock.yearsPerSecond * 365.25);
    clock.years += (run.t - before) / 365.25;
    remember();
  }
  draw();
  requestAnimationFrame(frame);
}

addEventListener("resize", () => { fit(); draw(); });
fit();
requestAnimationFrame((now) => { clock.last = now; frame(now); });
