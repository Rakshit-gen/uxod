from uxod import tools


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
