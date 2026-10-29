"""A self-contained HTML page that replays the runs."""

import html
import json

from . import sim

COLOURS = {"Sun": "#f5c542", "Mercury": "#9a9a9a", "Venus": "#d9b38c", "Earth": "#4f8fe8", "Mars": "#d0603a",
           "Jupiter": "#c99b6d", "Saturn": "#e2cf8f", "Uranus": "#8fd6d9", "Neptune": "#4a6fd6"}


def timeline(results: list[sim.Result]):
    """Every run's frames joined end to end, over every body that appeared."""
    names: list[str] = []
    for r in results:
        names += [n for n in r.names if n not in names]
    frames, years, offset = [], [], 0.0
    for r in results:
        for f, y in zip(r.frames, r.frame_years):
            where = dict(zip(r.names, f))
            frames.append([where.get(n) for n in names])
            years.append(round(offset + y, 3))
        offset += r.years
    return names, frames, years


def page(question: str, report: str, results: list[sim.Result]) -> str:
    names, frames, years = timeline(results)
    data = json.dumps({"names": names, "frames": frames, "years": years,
                       "colours": [COLOURS.get(n, "#ff4fd8") for n in names]})
    events = "".join(f"<li>{html.escape(e)}</li>" for r in results for e in r.events)
    return TEMPLATE.format(question=html.escape(question), report=html.escape(report),
                           events=events or "<li>Nothing collided or left.</li>", data=data)


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>uxod replay</title>
<style>
  body {{ margin: 0; background: #08090c; color: #d8d8d8; font: 15px/1.5 system-ui, sans-serif; }}
  main {{ max-width: 900px; margin: 0 auto; padding: 16px; }}
  h1 {{ font-size: 18px; font-weight: 600; margin: 8px 0; }}
  canvas {{ width: 100%; aspect-ratio: 1; background: #000; display: block; }}
  .bar {{ display: flex; gap: 12px; align-items: center; margin: 8px 0; }}
  input[type=range] {{ flex: 1; }}
  pre {{ white-space: pre-wrap; font: inherit; }}
  #year {{ font-variant-numeric: tabular-nums; min-width: 9ch; }}
</style></head>
<body><main>
<h1>{question}</h1>
<canvas id="sky" width="900" height="900" role="img" aria-label="The bodies moving over time"></canvas>
<div class="bar"><button id="play">Pause</button><input id="t" type="range" min="0" value="0"><span id="year"></span></div>
<pre>{report}</pre>
<ul>{events}</ul>
<p>Distances are drawn on a square-root scale so the inner planets and Neptune both fit.</p>
</main>
<script>
const D = {data};
const sky = document.getElementById("sky"), g = sky.getContext("2d");
const slider = document.getElementById("t"), label = document.getElementById("year");
slider.max = D.frames.length - 1;
let far = 1;
for (const f of D.frames) for (const p of f) if (p) far = Math.max(far, Math.hypot(p[0], p[1]));
far = Math.min(far, 60);
const scale = (v) => Math.sign(v) * Math.sqrt(Math.abs(v) / far) * 430;
const at = (p) => [450 + scale(p[0]), 450 - scale(p[1])];
let i = 0, playing = true;
function draw() {{
  g.fillStyle = "#000"; g.fillRect(0, 0, 900, 900);
  D.names.forEach((name, k) => {{
    g.strokeStyle = D.colours[k] + "55"; g.beginPath();
    let started = false;
    for (let j = Math.max(0, i - 150); j <= i; j++) {{
      const p = D.frames[j][k]; if (!p) {{ started = false; continue; }}
      const [x, y] = at(p); started ? g.lineTo(x, y) : g.moveTo(x, y); started = true;
    }}
    g.stroke();
    const p = D.frames[i][k]; if (!p) return;
    const [x, y] = at(p);
    g.fillStyle = D.colours[k]; g.beginPath(); g.arc(x, y, name === "Sun" ? 6 : 3.5, 0, 7); g.fill();
    g.fillText(name, x + 6, y - 6);
  }});
  slider.value = i; label.textContent = "year " + D.years[i].toFixed(1);
}}
document.getElementById("play").onclick = (e) => {{ playing = !playing; e.target.textContent = playing ? "Pause" : "Play"; }};
slider.oninput = () => {{ i = +slider.value; draw(); }};
setInterval(() => {{ if (playing) {{ i = (i + 1) % D.frames.length; draw(); }} }}, 33);
draw();
</script></body></html>
"""
