"""The agent: a model that turns a what-if into tool calls, runs the
simulation and reports what happened."""

import json
import os
import urllib.request

from . import tools

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
MAX_TURNS = 16

SYSTEM = """You are the Universe Extrapolater Orbital Destroyer. People ask what would happen if
something were done to the solar system. You set it up with the tools, run the simulation long enough
to see the consequences, and report.

How to work:
- Turn the question into tool calls. Pick sensible numbers when the question is vague and say which you picked.
- Masses: Earth is 3.0e-6 Msun, Jupiter 9.5e-4 Msun, a typical stellar black hole 10 Msun.
- After add_flyby, run at least closest_approach_in_years plus enough time for the effects to show.
- You may run more than once to watch things develop. Each run continues from the last.

How to report, in under 200 words:
- Start with the answer in one sentence.
- Use only numbers that a tool returned. Never estimate a number yourself.
- Say what changed for Earth: its distance range from the Sun and whether it stayed in the habitable zone.
- End with the energy error and one limit of the model that matters for this question: point masses,
  Newtonian gravity only, no tides, bodies that touch merge."""


def groq(messages, tool_specs, model):
    req = urllib.request.Request(
        GROQ_URL,
        data=json.dumps({"model": model, "messages": messages, "tools": tool_specs, "temperature": 0.2}).encode(),
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)["choices"][0]["message"]


def ask(question: str, chat=None, model: str | None = None, on_step=print):
    """Answers a what-if. Returns the report and the Universe, whose log
    can be replayed without a model."""
    chat = chat or groq
    model = model or os.environ.get("UXOD_MODEL", DEFAULT_MODEL)
    universe = tools.Universe()
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    for _ in range(MAX_TURNS):
        reply = chat(messages, tools.TOOLS, model)
        calls = reply.get("tool_calls") or []
        messages.append({"role": "assistant", "content": reply.get("content") or "", "tool_calls": calls}
                        if calls else {"role": "assistant", "content": reply.get("content") or ""})
        if not calls:
            return reply.get("content") or "", universe
        for call in calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
            except json.JSONDecodeError as e:
                out = {"error": f"arguments aren't JSON: {e}"}
            else:
                on_step(f"> {name}({', '.join(f'{k}={v}' for k, v in args.items())})")
                out = universe.call(name, args)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(out)})
    return f"Stopped after {MAX_TURNS} turns without a report.", universe

