import json
from pathlib import Path

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
    assert "Jupiter" not in gone  # with the Sun gone it is what the others leave


def test_a_stopped_earth_falls_into_the_sun():
    bodies = sim.solar_system()
    by_name(bodies, "Earth").vel *= 0.02
    sun_mass = by_name(bodies, "Sun").mass
    result = sim.run(bodies, 1)
    assert any("Earth hit Sun" in e for e in result.events)
    assert "Earth" not in result.after
    assert abs(by_name(bodies, "Sun").mass - sun_mass - 3.0404e-6) < 1e-12


def test_merging_conserves_momentum():
    bodies = sim.solar_system()
    by_name(bodies, "Earth").vel *= 0.02
    momentum = sum(b.mass * b.vel for b in bodies)
    sim.run(bodies, 1)
    assert np.allclose(sum(b.mass * b.vel for b in bodies), momentum, atol=1e-12)


def test_frames_cover_the_whole_run():
    result = sim.run(sim.solar_system(), 5, frames=50)
    assert result.frame_years[0] == 0 and result.frame_years[-1] == 5
    assert all(len(f) == len(result.names) for f in result.frames)


def test_a_close_pass_in_the_middle_of_a_run_is_caught():
    from uxod import tools

    u = tools.Universe()
    for name in sim.PLANETS:
        u.remove_body(name)
    # Fast enough that sampling every 20 steps misses the closest point by 0.012 AU.
    out = u.add_flyby("Rogue", 1, "mjup", 5, 30)
    result = u.call("run", {"years": 2 * out["closest_approach_in_years"]})
    assert abs(result["bodies"]["Rogue"]["sun_distance_range_au"][0] - 5) < 0.002


def test_a_flyby_from_beyond_the_ejection_distance_still_arrives():
    from uxod import tools

    u = tools.Universe()
    out = u.add_flyby("Rogue", 1, "mjup", 50, 20)
    assert out["starts_au"] > sim.EJECTED_AU
    result = u.call("run", {"years": 1})
    assert "Rogue" in result["bodies"]


def test_the_heaviest_body_orbits_nothing():
    snap = sim.snapshot(sim.solar_system())
    assert snap["Sun"]["orbits"] is None
    assert snap["Jupiter"]["orbits"] == "Sun"


def test_planets_keep_orbiting_the_sun_with_a_heavier_body_far_away():
    from uxod import tools

    u = tools.Universe()
    u.add_flyby("Black hole", 10, "msun", 20, 50)
    snap = u.list_bodies()
    assert snap["Sun"]["orbits"] == "Black hole"
    assert snap["Earth"]["orbits"] == "Sun" and snap["Earth"]["bound"]


def test_a_black_hole_flyby_never_ejects_the_sun():
    from uxod import agent

    plan = json.loads(Path("examples/black-hole.json").read_text())["plan"]
    u = agent.replay(plan, on_step=lambda s: None)
    lost = u.results[-1].events
    assert not any(e.split(": ")[1].startswith("Sun ") for e in lost)
    assert any("Black hole left" in e for e in lost)


def test_with_the_sun_gone_the_heaviest_body_is_the_anchor():
    bodies = sim.solar_system()
    bodies.remove(by_name(bodies, "Sun"))
    assert sim.anchor(bodies).name == "Jupiter"
