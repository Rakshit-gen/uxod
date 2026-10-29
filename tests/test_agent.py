import json

from uxod import agent


def scripted(*replies):
    """A stand-in for the model that gives these replies in turn."""
    seen = []

    def chat(messages, tool_specs, model):
        seen.append([dict(m) for m in messages])
        return replies[len(seen) - 1]

    return chat, seen


def call(id, name, /, **args):
    return {"id": id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def test_tool_results_go_back_to_the_model_and_the_report_comes_out():
    chat, seen = scripted(
        {"content": None, "tool_calls": [call("a", "remove_body", name="Jupiter"), call("b", "run", years=1)]},
        {"content": "Jupiter is gone."},
    )
    report, universe = agent.ask("delete jupiter", chat=chat, on_step=lambda s: None)
    assert report == "Jupiter is gone."
    tool_msgs = [m for m in seen[1] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["a", "b"]
    assert json.loads(tool_msgs[0]["content"]) == {"removed": "Jupiter"}
    assert [c["tool"] for c in universe.log] == ["remove_body", "run"]


def test_bad_arguments_are_reported_not_raised():
    chat, seen = scripted(
        {"tool_calls": [{"id": "a", "function": {"name": "run", "arguments": "{years: 1"}}]},
        {"content": "done"},
    )
    agent.ask("x", chat=chat, on_step=lambda s: None)
    assert "aren't JSON" in seen[1][-1]["content"]


def test_a_model_that_never_stops_is_cut_off():
    chat, _ = scripted(*[{"tool_calls": [call(str(i), "list_bodies")]} for i in range(agent.MAX_TURNS)])
    report, _ = agent.ask("x", chat=chat, on_step=lambda s: None)
    assert report.startswith("Stopped after")
