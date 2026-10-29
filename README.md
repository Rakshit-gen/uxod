# Universe Extrapolater Orbital Destroyer

Ask what would happen if you did something terrible to the solar system. An agent turns the question
into changes to a real n-body simulation of the Sun and eight planets, runs it forward, and tells you
what happened, using only numbers the simulation produced.

```
$ uxod replay examples/black-hole.json
> add_flyby(name=Black hole, mass=10, mass_unit=msun, closest_approach_au=20, speed_kms=50, angle_deg=120, inclination_deg=10)
> run(years=60)

year 27.02: Black hole left the system at 51.0 km/s
Energy error 5.3e-09, the worst of its runs.

wrote out/replay.html and out/plan.json
```

That is a saved plan, replayed without a model. `uxod ask "your question"` has the agent write the
plan itself; it saves `out/plan.json` with every tool call it made, so anyone can rerun its scenario
with `uxod replay` and no API key. `out/replay.html` animates the run.

## Quickstart

```
git clone https://github.com/Rakshit-gen/uxod && cd uxod
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/uxod replay examples/black-hole.json   # no key needed
export GROQ_API_KEY=...                           # https://console.groq.com/keys
.venv/bin/uxod ask "What if Earth stopped moving?"
```

The model defaults to `openai/gpt-oss-120b` on Groq; set `UXOD_MODEL` to use another.
