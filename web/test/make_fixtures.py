"""Writes what the Python simulation does with each example plan, for
sim.test.mjs to check the JavaScript against. Run from the repo root:
.venv/bin/python web/test/make_fixtures.py"""

import json
from pathlib import Path

from uxod import agent

out = {}
for path in sorted(Path("examples").glob("*.json")):
    universe = agent.replay(json.loads(path.read_text())["plan"], on_step=lambda s: None)
    out[path.stem] = {
        "events": [e for r in universe.results for e in r.events],
        "steps": [r.steps for r in universe.results],
        "bodies": {b.name: {"mass": b.mass, "pos": b.pos.tolist(), "vel": b.vel.tolist()} for b in universe.bodies},
    }
Path("web/test/fixtures.json").write_text(json.dumps(out, indent=1) + "\n")
