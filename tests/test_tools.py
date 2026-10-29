import numpy as np

from uxod import sim, tools


def test_bodies_are_found_by_name_in_any_case():
    u = tools.Universe()
    assert u.call("remove_body", {"name": "jupiter"}) == {"removed": "Jupiter"}
    assert "Jupiter" not in u.call("list_bodies", {})


def test_mistakes_come_back_as_errors_for_the_model():
    u = tools.Universe()
    assert "no body called Pluto" in u.call("remove_body", {"name": "Pluto"})["error"]
    assert "positive" in u.call("scale_mass", {"name": "Sun", "factor": 0})["error"]
    assert u.call("explode", {})["error"] == "no tool called explode"
    assert [c["tool"] for c in u.log] == ["remove_body", "scale_mass"]


def test_a_prograde_kick_raises_the_orbit():
    u = tools.Universe()
    before = u.list_bodies()["Mars"]["a_au"]
    after = u.call("kick", {"name": "Mars", "delta_v_kms": 3, "direction": "prograde"})["now"]["a_au"]
    assert after > before * 1.2
    assert "direction must be" in u.call("kick", {"name": "Mars", "delta_v_kms": 1, "direction": "up"})["error"]


def test_a_smash_conserves_momentum():
    u = tools.Universe()
    earth = u.body("Earth")
    m, v = earth.mass, earth.vel.copy()
    impactor = 3.0034e-6
    hit = 20 * sim.KMS * u._direction(earth, "retrograde")
    out = u.call("smash", {"target": "Earth", "impactor_mass": 1, "mass_unit": "mearth",
                           "speed_kms": 20, "direction": "retrograde"})
    assert np.allclose(earth.mass * earth.vel, m * v + impactor * (v + hit), rtol=0, atol=1e-15)
    assert abs(out["delta_v_kms"] - 20 * impactor / earth.mass) < 1e-4
    assert out["now"]["a_au"] < 1


def lone_sun():
    u = tools.Universe()
    for name in sim.PLANETS:
        u.remove_body(name)
    return u


def test_a_flyby_starts_far_out_on_an_unbound_path():
    u = lone_sun()
    out = u.call("add_flyby", {"name": "Rogue", "mass": 1, "mass_unit": "mjup", "closest_approach_au": 5,
                               "speed_kms": 10, "angle_deg": 40, "inclination_deg": 30})
    assert out["starts_au"] == 100
    rogue = u.list_bodies()["Rogue"]
    assert not rogue["bound"] and abs(rogue["distance_au"] - 100) < 0.1
    assert "already" in u.call("add_flyby", {"name": "rogue", "mass": 1, "mass_unit": "mjup",
                                             "closest_approach_au": 5, "speed_kms": 10})["error"]


def test_a_flyby_gets_as_close_as_asked_when_predicted():
    u = lone_sun()
    out = u.call("add_flyby", {"name": "Rogue", "mass": 1, "mass_unit": "mjup", "closest_approach_au": 5,
                               "speed_kms": 10, "angle_deg": 40, "inclination_deg": 30})
    first = u.call("run", {"years": out["closest_approach_in_years"]})
    assert abs(first["bodies"]["Rogue"]["distance_au"] - 5) < 0.01
    later = u.call("run", {"years": 20})
    assert abs(later["bodies"]["Rogue"]["sun_distance_range_au"][0] - 5) < 0.01


def test_runs_carry_on_from_each_other_and_are_capped():
    u = tools.Universe()
    u.call("run", {"years": 1})
    u.call("run", {"years": 1})
    assert len(u.results) == 2
    assert u.results[1].before["Earth"]["distance_au"] == u.results[0].after["Earth"]["distance_au"]
    assert "between 0 and 5000" in u.call("run", {"years": 6000})["error"]


def test_the_sun_cant_be_kicked_along_an_orbit_it_doesnt_have():
    u = tools.Universe()
    out = u.call("kick", {"name": "Sun", "delta_v_kms": 1, "direction": "prograde"})
    assert "orbits nothing" in out["error"]
