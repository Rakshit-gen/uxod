// The agent's tools from uxod/tools.py, for the page's buttons and for
// replaying plans the CLI saved.

import { AU_KM, DAYS_PER_YEAR, G, KMS, Run, anchor, cross, norm, orbit, primary, solarSystem, sub, toBarycentre } from "./sim.js";

export const MASS_UNITS = { msun: 1, mjup: 9.5479e-4, mearth: 3.0034e-6 };
export const DIRECTIONS = ["prograde", "retrograde", "outward", "inward", "north", "south"];
export const MAX_YEARS = 5000;

export class Universe {
  constructor() {
    this.bodies = solarSystem();
    this.log = [];
    this.events = [];
    this.current = null; // the run in progress, if any
  }

  call(tool, args) {
    if (!TOOLS.includes(tool)) throw new Error(`no tool called ${tool}`);
    this.log.push({ tool, args });
    return this[tool](args);
  }

  body(name) {
    const b = this.bodies.find((x) => x.name.toLowerCase() === String(name).toLowerCase());
    if (!b) throw new Error(`no body called ${name}; there are ${this.bodies.map((x) => x.name).join(", ")}`);
    return b;
  }

  remove_body({ name }) {
    const b = this.body(name);
    this.bodies.splice(this.bodies.indexOf(b), 1);
    return { removed: b.name };
  }

  scale_mass({ name, factor }) {
    if (!(factor > 0)) throw new Error("factor must be positive; use remove_body to delete a body");
    const b = this.body(name);
    b.mass *= factor;
    return { name: b.name, mass_msun: b.mass };
  }

  kick({ name, delta_v_kms, direction }) {
    const b = this.body(name);
    const u = this.direction(b, direction);
    b.vel = b.vel.map((v, k) => v + delta_v_kms * KMS * u[k]);
    return { name: b.name, now: orbit(this.bodies, b) };
  }

  smash({ target, impactor_mass, mass_unit, speed_kms, direction }) {
    const b = this.body(target);
    const m = impactor_mass * unit(mass_unit);
    const u = this.direction(b, direction);
    b.vel = b.vel.map((v, k) => (b.mass * v + m * (v + speed_kms * KMS * u[k])) / (b.mass + m));
    b.mass += m;
    return { name: b.name, mass_msun: b.mass, delta_v_kms: (speed_kms * m) / b.mass, now: orbit(this.bodies, b) };
  }

  add_flyby({ name, mass, mass_unit, closest_approach_au, speed_kms, angle_deg = 0, inclination_deg = 0, radius_km = 0 }) {
    if (this.bodies.some((b) => b.name.toLowerCase() === name.toLowerCase())) throw new Error(`there is already a body called ${name}`);
    if (!(closest_approach_au > 0 && speed_kms > 0)) throw new Error("closest_approach_au and speed_kms must be positive");
    const sun = this.body("Sun");
    const m = mass * unit(mass_unit);
    const mu = G * (sun.mass + m);
    const vInf = speed_kms * KMS;
    const a = -mu / vInf ** 2;
    const e = 1 + (closest_approach_au * vInf ** 2) / mu;
    const p = a * (1 - e * e);
    const start = Math.max(100, 5 * closest_approach_au);
    const f = -Math.acos((p / start - 1) / e);
    const r = p / (1 + e * Math.cos(f));
    const pos = [r * Math.cos(f), r * Math.sin(f), 0];
    const s = Math.sqrt(mu / p);
    const vel = [-s * Math.sin(f), s * (e + Math.cos(f)), 0];
    const w = (angle_deg * Math.PI) / 180, i = (inclination_deg * Math.PI) / 180;
    // Rz(angle) then Rx(inclination), as in tools.py.
    const rot = (v) => {
      const y = Math.cos(i) * v[1] - Math.sin(i) * v[2], z = Math.sin(i) * v[1] + Math.cos(i) * v[2];
      return [Math.cos(w) * v[0] - Math.sin(w) * y, Math.sin(w) * v[0] + Math.cos(w) * y, z];
    };
    const F = Math.acosh((1 - start / a) / e);
    const arrive = (e * Math.sinh(F) - F) / Math.sqrt(mu / (-a) ** 3) / DAYS_PER_YEAR;
    const rp = rot(pos), rv = rot(vel);
    this.bodies.push({ name, mass: m, pos: sun.pos.map((x, k) => x + rp[k]), vel: sun.vel.map((x, k) => x + rv[k]), radius: radius_km / AU_KM });
    toBarycentre(this.bodies);
    return { name, mass_msun: m, starts_au: start, closest_approach_in_years: Math.round(arrive * 100) / 100 };
  }

  // Starts a run and returns it; the caller advances it, a little per frame or all at once.
  run({ years }) {
    if (!(years > 0 && years <= MAX_YEARS)) throw new Error(`years must be between 0 and ${MAX_YEARS}`);
    this.current = new Run(this.bodies, years);
    return this.current;
  }

  list_bodies() {
    return Object.fromEntries(this.bodies.map((b) => [b.name, { mass_msun: b.mass, ...orbit(this.bodies, b) }]));
  }

  direction(b, direction) {
    if (!DIRECTIONS.includes(direction)) throw new Error(`direction must be one of ${DIRECTIONS.join(", ")}`);
    const host = primary(this.bodies, b);
    if (!host) throw new Error(`${b.name} is the heaviest body and orbits nothing, so ${direction} means nothing`);
    const r = sub(b.pos, host.pos), v = sub(b.vel, host.vel);
    const n = cross(r, v);
    const u = { prograde: v, retrograde: v.map((x) => -x), outward: r, inward: r.map((x) => -x), north: n, south: n.map((x) => -x) }[direction];
    const len = norm(u);
    return u.map((x) => x / len);
  }

  anchor() {
    return anchor(this.bodies);
  }
}

const TOOLS = ["list_bodies", "remove_body", "scale_mass", "kick", "smash", "add_flyby", "run"];

function unit(name) {
  if (!(name in MASS_UNITS)) throw new Error(`mass_unit must be one of ${Object.keys(MASS_UNITS).join(", ")}`);
  return MASS_UNITS[name];
}

// Runs a whole saved plan at once. Returns the universe and every run's events.
export function replay(plan) {
  const u = new Universe();
  const runs = [];
  for (const { tool, args } of plan) {
    const out = u.call(tool, args);
    if (tool === "run") {
      out.advance();
      runs.push(out);
    }
  }
  return { universe: u, runs };
}
