// The solar system simulation from uxod/sim.py, in AU, days and solar
// masses. It follows the Python step for step so the two agree.

export const G = 0.01720209895 ** 2;
export const AU_KM = 1.495978707e8;
export const KMS = 86400 / AU_KM;
export const DAYS_PER_YEAR = 365.25;

// J2000 elements from JPL's "Approximate Positions of the Planets":
// a, e, inclination, mean longitude, longitude of perihelion, node, mass, radius in km.
export const PLANETS = {
  Mercury: [0.38709927, 0.20563593, 7.00497902, 252.2503235, 77.45779628, 48.33076593, 1.6601e-7, 2440],
  Venus: [0.72333566, 0.00677672, 3.39467605, 181.9790995, 131.60246718, 76.67984255, 2.4478e-6, 6052],
  Earth: [1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0, 3.0404e-6, 6371],
  Mars: [1.52371034, 0.0933941, 1.84969142, -4.55343205, -23.94362959, 49.55953891, 3.2272e-7, 3390],
  Jupiter: [5.202887, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909, 9.5479e-4, 69911],
  Saturn: [9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448, 2.8589e-4, 58232],
  Uranus: [19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.9542763, 74.01692503, 4.3662e-5, 25362],
  Neptune: [30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574, 5.1514e-5, 24622],
};
const SUN_RADIUS_KM = 695700;
const rad = (d) => (d * Math.PI) / 180;

export function fromElements(a, e, inc, meanLong, longPeri, node, mu) {
  inc = rad(inc);
  node = rad(node);
  const peri = rad(longPeri) - node;
  const m = rad(meanLong - longPeri);
  let E = m;
  for (let k = 0; k < 50; k++) E -= (E - e * Math.sin(E) - m) / (1 - e * Math.cos(E));
  const x = a * (Math.cos(E) - e), y = a * Math.sqrt(1 - e * e) * Math.sin(E);
  const n = Math.sqrt(mu / a ** 3);
  const edot = n / (1 - e * Math.cos(E));
  const vx = -a * Math.sin(E) * edot, vy = a * Math.sqrt(1 - e * e) * Math.cos(E) * edot;
  const [cw, sw, cn, sn, ci, si] = [Math.cos(peri), Math.sin(peri), Math.cos(node), Math.sin(node), Math.cos(inc), Math.sin(inc)];
  const rotate = (px, py) => [
    (cw * cn - sw * sn * ci) * px + (-sw * cn - cw * sn * ci) * py,
    (cw * sn + sw * cn * ci) * px + (-sw * sn + cw * cn * ci) * py,
    sw * si * px + cw * si * py,
  ];
  return { pos: rotate(x, y), vel: rotate(vx, vy) };
}

export function toBarycentre(bodies) {
  const m = bodies.reduce((s, b) => s + b.mass, 0);
  for (const key of ["pos", "vel"]) {
    const c = [0, 1, 2].map((k) => bodies.reduce((s, b) => s + b.mass * b[key][k], 0) / m);
    for (const b of bodies) b[key] = b[key].map((v, k) => v - c[k]);
  }
}

export function solarSystem() {
  const bodies = [{ name: "Sun", mass: 1, pos: [0, 0, 0], vel: [0, 0, 0], radius: SUN_RADIUS_KM / AU_KM }];
  for (const [name, [a, e, inc, L, lp, node, mass, radius]] of Object.entries(PLANETS)) {
    const { pos, vel } = fromElements(a, e, inc, L, lp, node, G * (1 + mass));
    bodies.push({ name, mass, pos, vel, radius: radius / AU_KM });
  }
  toBarycentre(bodies);
  return bodies;
}

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
export const norm = (a) => Math.sqrt(dot(a, a));
export { sub, dot, cross };

// Accelerations, and squared distances between every pair (Infinity on the diagonal).
export function accelerations(bodies) {
  const n = bodies.length;
  const acc = bodies.map(() => [0, 0, 0]);
  const r2 = Array.from({ length: n }, () => new Array(n).fill(Infinity));
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const d = sub(bodies[j].pos, bodies[i].pos);
      const s = dot(d, d);
      r2[i][j] = r2[j][i] = s;
      const inv = G / s ** 1.5;
      for (let k = 0; k < 3; k++) {
        acc[i][k] += bodies[j].mass * inv * d[k];
        acc[j][k] -= bodies[i].mass * inv * d[k];
      }
    }
  }
  return { acc, r2 };
}

export function energy(bodies) {
  let e = 0;
  for (let i = 0; i < bodies.length; i++) {
    e += 0.5 * bodies[i].mass * dot(bodies[i].vel, bodies[i].vel);
    for (let j = i + 1; j < bodies.length; j++) {
      e -= (G * bodies[i].mass * bodies[j].mass) / norm(sub(bodies[i].pos, bodies[j].pos));
    }
  }
  return e;
}

// Of the bodies at least as heavy, the one pulling hardest. The heaviest orbits nothing.
export function primary(bodies, body) {
  let best = null, pull = -1;
  for (const h of bodies) {
    if (h === body || h.mass < body.mass) continue;
    const d = sub(h.pos, body.pos);
    const p = h.mass / dot(d, d);
    if (p > pull) [best, pull] = [h, p];
  }
  return best;
}

export function orbit(bodies, body) {
  const host = primary(bodies, body);
  if (!host) return { orbits: null };
  const r = sub(body.pos, host.pos), v = sub(body.vel, host.vel);
  const mu = G * (host.mass + body.mass);
  const dist = norm(r);
  const specific = dot(v, v) / 2 - mu / dist;
  const h = cross(r, v);
  const e = Math.sqrt(Math.max(0, 1 + (2 * specific * dot(h, h)) / mu ** 2));
  const out = { orbits: host.name, distance_au: dist, e, bound: specific < 0 };
  if (specific < 0) {
    out.a_au = -mu / (2 * specific);
    out.period_years = (2 * Math.PI * Math.sqrt(out.a_au ** 3 / mu)) / DAYS_PER_YEAR;
  }
  return out;
}

// The Sun, or the heaviest body once the Sun is gone.
export function anchor(bodies) {
  return bodies.find((b) => b.name === "Sun") || bodies.reduce((a, b) => (b.mass > a.mass ? b : a));
}

export const EJECTED_AU = 200;
export const HABITABLE_AU = [0.95, 1.67];
const round3 = (x) => Math.round(x * 1000) / 1000;

// A run of `years`, stepped a little at a time so a page can draw between
// steps. Same leapfrog, step size, merges and ejections as sim.run.
export class Run {
  constructor(bodies, years, maxSteps = 3_000_000) {
    this.bodies = bodies;
    this.end = years * DAYS_PER_YEAR;
    this.maxSteps = maxSteps;
    this.t = 0;
    this.steps = 0;
    this.events = [];
    this.lost = 0;
    let shortest = Infinity;
    for (const b of bodies) {
      const o = orbit(bodies, b);
      if (o.period_years) shortest = Math.min(shortest, round3(o.period_years));
    }
    if (shortest === Infinity) shortest = 1;
    this.base = Math.min((shortest * DAYS_PER_YEAR) / 60, 4);
    this.e0 = energy(bodies);
    ({ acc: this.acc, r2: this.r2 } = accelerations(bodies));
    this.closest = {};
    this.farthest = {};
    this.track();
  }

  get done() {
    return this.t >= this.end || this.steps >= this.maxSteps;
  }

  get energyError() {
    return Math.abs((energy(this.bodies) + this.lost - this.e0) / this.e0);
  }

  timeStep() {
    const { bodies, r2 } = this;
    let best = Infinity, bi = 0, bj = 1;
    for (let i = 0; i < bodies.length; i++) {
      for (let j = i + 1; j < bodies.length; j++) {
        const s = r2[i][j] ** 1.5 / (bodies[i].mass + bodies[j].mass);
        if (s < best) [best, bi, bj] = [s, i, j];
      }
    }
    const r = Math.sqrt(r2[bi][bj]);
    const v = norm(sub(bodies[bi].vel, bodies[bj].vel));
    const freeFall = Math.sqrt(r ** 3 / (G * (bodies[bi].mass + bodies[bj].mass)));
    return Math.min(this.base, 0.02 * freeFall, (0.05 * r) / Math.max(v, 1e-12));
  }

  // Advances until `days` more have passed or the run ends.
  advance(days = Infinity) {
    const stop = Math.min(this.end, this.t + days);
    while (this.t < stop) {
      if (this.steps >= this.maxSteps) {
        this.events.push(`stopped after ${this.steps} steps at year ${(this.t / DAYS_PER_YEAR).toFixed(1)}: an encounter needed steps too short to finish`);
        return;
      }
      this.step(Math.min(this.timeStep(), this.end - this.t));
    }
  }

  step(dt) {
    const { bodies } = this;
    bodies.forEach((b, i) => {
      for (let k = 0; k < 3; k++) b.vel[k] += 0.5 * dt * this.acc[i][k];
      for (let k = 0; k < 3; k++) b.pos[k] += dt * b.vel[k];
    });
    ({ acc: this.acc, r2: this.r2 } = accelerations(bodies));
    bodies.forEach((b, i) => {
      for (let k = 0; k < 3; k++) b.vel[k] += 0.5 * dt * this.acc[i][k];
    });
    this.t += dt;
    this.steps += 1;
    this.track();
  }

  track() {
    const sun = this.bodies.find((b) => b.name === "Sun");
    if (!sun) return;
    for (const b of this.bodies) {
      if (b === sun) continue;
      const d = norm(sub(b.pos, sun.pos));
      this.closest[b.name] = Math.min(this.closest[b.name] ?? Infinity, d);
      this.farthest[b.name] = Math.max(this.farthest[b.name] ?? 0, d);
    }
  }
}
