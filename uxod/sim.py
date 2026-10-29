"""An n-body simulation of the solar system, in AU, days and solar masses."""

from dataclasses import dataclass

import numpy as np

G = 0.01720209895**2  # Gauss's constant squared: AU^3 / (Msun day^2)
KMS = 86400 / 1.495978707e8  # km/s in AU/day
DAYS_PER_YEAR = 365.25

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
