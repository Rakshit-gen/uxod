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
