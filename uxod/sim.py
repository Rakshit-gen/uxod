"""An n-body simulation of the solar system, in AU, days and solar masses."""

from dataclasses import dataclass, field

import numpy as np

G = 0.01720209895**2  # Gauss's constant squared: AU^3 / (Msun day^2)
KMS = 86400 / 1.495978707e8  # km/s in AU/day
DAYS_PER_YEAR = 365.25
EJECTED_AU = 200  # unbound, this far from the anchor and moving away
HABITABLE_AU = (0.95, 1.67)  # a rough habitable zone for today's Sun

# J2000 elements from JPL's "Approximate Positions of the Planets" (Standish):
# a (AU), e, inclination, mean longitude, longitude of perihelion, longitude
# of the ascending node (degrees), then mass in solar masses and radius in km.
PLANETS = {
    "Mercury": (0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593, 1.6601e-7, 2440),
    "Venus": (0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255, 2.4478e-6, 6052),
    "Earth": (1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0, 3.0404e-6, 6371),
    "Mars": (1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891, 3.2272e-7, 3390),
    "Jupiter": (5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909, 9.5479e-4, 69911),
    "Saturn": (9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448, 2.8589e-4, 58232),
    "Uranus": (19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503, 4.3662e-5, 25362),
    "Neptune": (30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574, 5.1514e-5, 24622),
}
SUN_RADIUS_KM = 695700


@dataclass
class Body:
    name: str
    mass: float  # Msun
    pos: np.ndarray  # AU
    vel: np.ndarray  # AU/day
    radius: float  # AU


@dataclass
class Result:
    years: float
    events: list[str]
    before: dict[str, dict]
    after: dict[str, dict]
    energy_error: float
    steps: int
    names: list[str] = field(default_factory=list)
    frames: list[list] = field(default_factory=list)  # per frame, [x, y] or None per name
    frame_years: list[float] = field(default_factory=list)


def from_elements(a, e, inc, mean_long, long_peri, node, mu):
    """Position and velocity relative to the central body."""
    inc, node = np.radians(inc), np.radians(node)
    peri = np.radians(long_peri) - node
    m = np.radians(mean_long - long_peri)
    E = m
    for _ in range(50):
        E -= (E - e * np.sin(E) - m) / (1 - e * np.cos(E))
    x, y = a * (np.cos(E) - e), a * np.sqrt(1 - e * e) * np.sin(E)
    n = np.sqrt(mu / a**3)
    edot = n / (1 - e * np.cos(E))
    vx, vy = -a * np.sin(E) * edot, a * np.sqrt(1 - e * e) * np.cos(E) * edot

    def rotate(px, py):
        cw, sw, cn, sn, ci, si = np.cos(peri), np.sin(peri), np.cos(node), np.sin(node), np.cos(inc), np.sin(inc)
        return np.array([
            (cw * cn - sw * sn * ci) * px + (-sw * cn - cw * sn * ci) * py,
            (cw * sn + sw * cn * ci) * px + (-sw * sn + cw * cn * ci) * py,
            (sw * si) * px + (cw * si) * py,
        ])

    return rotate(x, y), rotate(vx, vy)


def solar_system() -> list[Body]:
    bodies = [Body("Sun", 1.0, np.zeros(3), np.zeros(3), SUN_RADIUS_KM / 1.495978707e8)]
    for name, (a, e, inc, mean_long, long_peri, node, mass, radius) in PLANETS.items():
        pos, vel = from_elements(a, e, inc, mean_long, long_peri, node, G * (1 + mass))
        bodies.append(Body(name, mass, pos, vel, radius / 1.495978707e8))
    to_barycentre(bodies)
    return bodies


def to_barycentre(bodies):
    m = sum(b.mass for b in bodies)
    cp = sum(b.mass * b.pos for b in bodies) / m
    cv = sum(b.mass * b.vel for b in bodies) / m
    for b in bodies:
        b.pos = b.pos - cp
        b.vel = b.vel - cv


def accelerations(pos, mass):
    d = pos[None, :, :] - pos[:, None, :]
    r2 = (d**2).sum(-1)
    np.fill_diagonal(r2, np.inf)
    return G * (d * (mass[None, :] / r2**1.5)[:, :, None]).sum(1), r2


def energy(pos, vel, mass):
    kinetic = 0.5 * (mass * (vel**2).sum(1)).sum()
    d = np.sqrt(((pos[None] - pos[:, None]) ** 2).sum(-1))
    i, j = np.triu_indices(len(mass), 1)
    return kinetic - G * (mass[i] * mass[j] / d[i, j]).sum()


def primary(bodies, body):
    """The body this one orbits: of the bodies at least as heavy, the one
    pulling hardest, which is the Sun unless something heavy comes close.
    The heaviest body orbits nothing."""
    heavier = [b for b in bodies if b is not body and b.mass >= body.mass]
    if not heavier:
        return None
    return max(heavier, key=lambda h: h.mass / float((h.pos - body.pos) @ (h.pos - body.pos)))


def orbit(bodies, body):
    """Semi-major axis, eccentricity and distance relative to the primary."""
    host = primary(bodies, body)
    if host is None:
        return {"orbits": None}
    r = body.pos - host.pos
    v = body.vel - host.vel
    mu = G * (host.mass + body.mass)
    dist = float(np.linalg.norm(r))
    specific = float(v @ v) / 2 - mu / dist
    h = np.cross(r, v)
    e = float(np.sqrt(max(0.0, 1 + 2 * specific * (h @ h) / mu**2)))
    out = {"orbits": host.name, "distance_au": round(dist, 4), "e": round(e, 4), "bound": specific < 0}
    if specific < 0:
        a = -mu / (2 * specific)
        out["a_au"] = round(a, 4)
        out["period_years"] = round(float(2 * np.pi * np.sqrt(a**3 / mu)) / DAYS_PER_YEAR, 3)
    return out


def snapshot(bodies):
    return {b.name: {"mass_msun": b.mass, **orbit(bodies, b)} for b in bodies}


def anchor(bodies):
    """What "the system" means: the Sun, or the heaviest body once the Sun is gone."""
    return next((b for b in bodies if b.name == "Sun"), None) or max(bodies, key=lambda b: b.mass)


def leaving(bodies):
    """Bodies unbound from the anchor, EJECTED_AU from it and moving away."""
    a = anchor(bodies)
    out = []
    for b in bodies:
        if b is a:
            continue
        r, v = b.pos - a.pos, b.vel - a.vel
        dist = np.sqrt(r @ r)
        if dist > EJECTED_AU and r @ v > 0 and (v @ v) / 2 > G * (a.mass + b.mass) / dist:
            out.append(b)
    return out


def time_step(r2, vel, pair_mass, base):
    """A step short enough for the closest pair: a fiftieth of their free-fall time."""
    i, j = divmod(int(np.argmin(r2**1.5 / pair_mass)), len(r2))
    r = np.sqrt(r2[i, j])
    dv = vel[i] - vel[j]
    v = np.sqrt(dv @ dv)
    free_fall = np.sqrt(r**3 / (G * pair_mass[i, j]))
    return min(base, 0.02 * free_fall, 0.05 * r / max(v, 1e-12))


def run(bodies: list[Body], years: float, frames: int = 600, max_steps: int = 3_000_000) -> Result:
    """Advances the bodies in place by `years` with a kick-drift-kick
    leapfrog. Bodies that touch merge, conserving momentum; bodies that
    leave the anchor (see leaving) are dropped."""
    before = snapshot(bodies)
    names = [b.name for b in bodies]
    events: list[str] = []
    end = years * DAYS_PER_YEAR
    shortest = min((o["period_years"] for o in before.values() if o.get("period_years")), default=1.0)
    base = min(shortest * DAYS_PER_YEAR / 60, 4.0)

    def arrays():
        return (np.array([b.pos for b in bodies]), np.array([b.vel for b in bodies]),
                np.array([b.mass for b in bodies]), np.array([b.radius for b in bodies]))

    def pairs():
        return mass[None] + mass[:, None], (radii[None] + radii[:, None]) ** 2

    pos, vel, mass, radii = arrays()
    pair_mass, reach = pairs()
    e0 = energy(pos, vel, mass)
    lost = 0.0  # energy carried off by merges and ejections, so it isn't counted as error
    acc, r2 = accelerations(pos, mass)
    t, steps = 0.0, 0
    every = end / frames
    result = Result(years, events, before, {}, 0.0, 0, names)

    def record():
        where = {b.name: [round(float(b.pos[0]), 4), round(float(b.pos[1]), 4)] for b in bodies}
        result.frames.append([where.get(n) for n in names])
        result.frame_years.append(round(t / DAYS_PER_YEAR, 3))

    def sync():
        for b, p, v in zip(bodies, pos, vel):
            b.pos, b.vel = p.copy(), v.copy()

    closest: dict[str, float] = {}
    farthest: dict[str, float] = {}
    lo = hi = None  # per-step running minimum and maximum, aligned with bodies

    def track():
        # Distances from the Sun, while it's still there.
        nonlocal lo, hi
        sun = next((k for k, b in enumerate(bodies) if b.name == "Sun"), None)
        if sun is None:
            return
        d = np.sqrt(((pos - pos[sun]) ** 2).sum(1))
        lo = d if lo is None else np.minimum(lo, d)
        hi = d if hi is None else np.maximum(hi, d)

    def flush():
        # Called before the list of bodies changes.
        nonlocal lo, hi
        if lo is not None:
            for b, a, z in zip(bodies, lo, hi):
                if b.name != "Sun":
                    closest[b.name] = min(closest.get(b.name, np.inf), float(a))
                    farthest[b.name] = max(farthest.get(b.name, 0.0), float(z))
        lo = hi = None

    record()
    track()
    next_frame = every
    while t < end:
        if steps >= max_steps:
            events.append(f"stopped after {steps} steps at year {t / DAYS_PER_YEAR:.1f}: an encounter needed steps too short to finish")
            break
        dt = min(time_step(r2, vel, pair_mass, base), end - t)
        vel += 0.5 * dt * acc
        pos += dt * vel
        acc, r2 = accelerations(pos, mass)
        vel += 0.5 * dt * acc
        t += dt
        steps += 1
        track()

        touching = np.argwhere(np.triu(r2 < reach, 1)) if (r2 < reach).any() else ()
        if len(touching) or steps % 200 == 0 or t >= next_frame:
            sync()
        if len(touching):
            i, j = touching[0]
            big, small = (bodies[i], bodies[j]) if mass[i] >= mass[j] else (bodies[j], bodies[i])
            flush()
            before_e = energy(pos, vel, mass)
            m = big.mass + small.mass
            big.vel = (big.mass * big.vel + small.mass * small.vel) / m
            big.pos = (big.mass * big.pos + small.mass * small.pos) / m
            big.radius = max(big.radius, small.radius)
            big.mass = m
            bodies.remove(small)
            events.append(f"year {t / DAYS_PER_YEAR:.2f}: {small.name} hit {big.name} and merged into it")
            pos, vel, mass, radii = arrays()
            pair_mass, reach = pairs()
            lost += before_e - energy(pos, vel, mass)
            acc, r2 = accelerations(pos, mass)
        elif steps % 200 == 0:
            gone = leaving(bodies)
            if gone:
                flush()
            for b in gone:
                before_e = energy(pos, vel, mass)
                bodies.remove(b)
                speed = np.linalg.norm(b.vel - anchor(bodies).vel) / KMS
                events.append(f"year {t / DAYS_PER_YEAR:.2f}: {b.name} left the system at {speed:.1f} km/s")
                pos, vel, mass, radii = arrays()
                pair_mass, reach = pairs()
                lost += before_e - energy(pos, vel, mass)
            if gone:
                acc, r2 = accelerations(pos, mass)
        if t >= next_frame:
            record()
            next_frame += every

    sync()
    flush()
    if result.frame_years[-1] != round(t / DAYS_PER_YEAR, 3):
        record()
    result.after = snapshot(bodies)
    for b in bodies:
        if b.name in closest:
            result.after[b.name]["sun_distance_range_au"] = [round(closest[b.name], 3), round(farthest[b.name], 3)]
    if "Earth" in closest and "Earth" in result.after:
        result.after["Earth"]["stayed_habitable"] = (
            HABITABLE_AU[0] <= closest["Earth"] and farthest["Earth"] <= HABITABLE_AU[1])
    result.steps = steps
    result.energy_error = float(abs((energy(pos, vel, mass) + lost - e0) / e0))
    return result
