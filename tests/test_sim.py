import numpy as np

from uxod import sim


def by_name(bodies, name):
    return next(b for b in bodies if b.name == name)


def test_earth_starts_at_perihelion_speed():
    # J2000 is 1 January, two days before Earth's perihelion.
    bodies = sim.solar_system()
    earth, sun = by_name(bodies, "Earth"), by_name(bodies, "Sun")
    assert abs(np.linalg.norm(earth.pos - sun.pos) - 0.9833) < 1e-3
    assert abs(np.linalg.norm(earth.vel - sun.vel) / sim.KMS - 30.29) < 0.05


def test_orbits_match_the_elements():
    snap = sim.snapshot(sim.solar_system())
    for name, (a, e, *_rest) in sim.PLANETS.items():
        assert abs(snap[name]["a_au"] - a) / a < 0.01, name
        assert abs(snap[name]["e"] - e) < 0.01, name
