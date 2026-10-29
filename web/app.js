import { Universe } from "./tools.js";

const COLOURS = { Sun: "#f5c542", Mercury: "#9a9a9a", Venus: "#d9b38c", Earth: "#4f8fe8", Mars: "#d0603a",
  Jupiter: "#c99b6d", Saturn: "#e2cf8f", Uranus: "#8fd6d9", Neptune: "#4a6fd6" };
const colour = (name) => COLOURS[name] || "#ff4fd8";

const sky = document.getElementById("sky");
const g = sky.getContext("2d");
let universe = new Universe();
const view = { extent: 40 }; // AU at the edge of the view, before the square-root squeeze

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

addEventListener("resize", () => { fit(); draw(); });
fit();
draw();
