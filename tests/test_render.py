from uxod import render, tools


def test_runs_join_into_one_timeline_even_when_bodies_come_and_go():
    u = tools.Universe()
    u.run(1)
    u.add_flyby("Rogue", 1, "mjup", 50, 20)
    u.run(1)
    names, frames, years = render.timeline(u.results)
    assert names[-1] == "Rogue"
    assert frames[0][-1] is None and frames[-1][-1] is not None
    assert years[-1] == 2 and years == sorted(years)
    assert all(len(f) == len(names) for f in frames)
