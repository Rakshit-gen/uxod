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

## What the examples show

Each of these is a plan in `examples/`, replayed with `uxod replay`. The numbers are what the runs
printed on 29 October 2026; `tests/test_examples.py` replays all of them.

| Plan | What happened |
|---|---|
| `black-hole.json`: 10 solar masses, 20 AU from the Sun, 50 km/s | Neptune was thrown out (e 1.06). Saturn and Uranus were knocked onto orbits that dip to 0.30 and 0.35 AU, inside Earth's. Jupiter's semi-major axis went from 5.20 to 9.94 AU. Earth's eccentricity only went from 0.017 to 0.024. |
| `earth-smash.json`: a Mars-mass body hits Earth head-on at 20 km/s | Earth dropped to a 0.888 AU orbit with e 0.108, swinging between 0.792 and 0.984 AU, out of the habitable zone at its closest. |
| `half-sun.json`: the Sun loses half its mass at once | In 300 years Mars, Earth, Saturn, Jupiter and Venus left, Mars first at year 116 and Earth at year 180. Mercury stayed bound (e 0.59), and Uranus and Neptune stayed on stretched orbits with e 0.91 and 0.99. |
| `jupiter-star.json`: Jupiter 80 times heavier | Within 300 years Saturn was on an escape orbit (e 1.04) and Uranus's eccentricity went from 0.05 to 0.40. Earth stayed between 0.971 and 1.029 AU. |
| `no-sun.json`: the Sun vanishes | The planets went off in straight lines. Mercury passed 200 AU (measured from Jupiter) at year 19.7. |
