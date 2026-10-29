import argparse
import json
import os
import sys
from pathlib import Path

from . import agent, render, tools


def save(out: Path, question: str, report: str, universe: tools.Universe):
    out.mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps({"question": question, "plan": universe.log}, indent=2) + "\n")
    (out / "replay.html").write_text(render.page(question, report, universe.results))
    print(f"\nwrote {out / 'replay.html'} and {out / 'plan.json'}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="uxod", description="Universe extrapolater orbital destroyer")
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("ask", help="ask a what-if; needs GROQ_API_KEY")
    a.add_argument("question")
    a.add_argument("-o", "--out", type=Path, default=Path("out"))
    r = sub.add_parser("replay", help="run a saved plan.json again, no model needed")
    r.add_argument("plan", type=Path)
    r.add_argument("-o", "--out", type=Path, default=Path("out"))
    sub.add_parser("bodies", help="print the solar system at J2000")
    args = p.parse_args(argv)

    if args.command == "bodies":
        for name, o in tools.Universe().list_bodies().items():
            print(f"{name:8} a={o.get('a_au', '-'):>8} AU  e={o.get('e', '-')}")
        return 0
    if args.command == "ask":
        if not os.environ.get("GROQ_API_KEY"):
            print("GROQ_API_KEY isn't set. Get one at https://console.groq.com/keys", file=sys.stderr)
            return 2
        report, universe = agent.ask(args.question)
        print("\n" + report)
        save(args.out, args.question, report, universe)
        return 0
    saved = json.loads(args.plan.read_text())
    universe = agent.replay(saved["plan"])
    events = [e for r in universe.results for e in r.events]
    report = "\n".join(events) or "Replayed; nothing collided or left."
    if universe.results:
        report += f"\nEnergy error {max(r.energy_error for r in universe.results):.1e}, the worst of its runs."
    print("\n" + report)
    save(args.out, saved.get("question", args.plan.stem), report, universe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
