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


def test_a_century_keeps_the_planets_where_they_were():
    bodies = sim.solar_system()
    result = sim.run(bodies, 100)
    assert result.events == []
    assert result.energy_error < 1e-5
    for name in sim.PLANETS:
        assert abs(result.after[name]["a_au"] - result.before[name]["a_au"]) / result.before[name]["a_au"] < 0.01
    assert result.after["Earth"]["stayed_habitable"]


def test_without_the_sun_everything_leaves():
    bodies = sim.solar_system()
    bodies.remove(by_name(bodies, "Sun"))
    result = sim.run(bodies, 60)
    gone = [e.split(": ")[1].split()[0] for e in result.events]
    assert {"Mercury", "Venus", "Earth"} <= set(gone)
    assert "Earth left the system at 30.3 km/s" in " ".join(result.events)
