import json
from pathlib import Path

import pytest

from uxod import agent

EXAMPLES = sorted(Path("examples").glob("*.json"))


@pytest.mark.parametrize("path", EXAMPLES, ids=[p.stem for p in EXAMPLES])
def test_every_example_replays(path):
    saved = json.loads(path.read_text())
    assert saved["question"].endswith("?")
    universe = agent.replay(saved["plan"], on_step=lambda s: None)
    assert universe.results and all(r.energy_error < 1e-4 for r in universe.results)


def test_a_head_on_hit_pushes_earth_out_of_the_habitable_zone():
    saved = json.loads(Path("examples/earth-smash.json").read_text())
    earth = agent.replay(saved["plan"], on_step=lambda s: None).results[-1].after["Earth"]
    assert earth["stayed_habitable"] is False
    assert earth["sun_distance_range_au"][0] < 0.8
