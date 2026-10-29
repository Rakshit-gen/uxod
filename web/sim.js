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
