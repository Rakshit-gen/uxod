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


def test_a_logged_plan_replays_without_a_model():
    chat, _ = scripted(
        {"tool_calls": [call("a", "scale_mass", name="Sun", factor=0.5), call("b", "run", years=2)]},
        {"content": "ok"},
    )
    _, live = agent.ask("halve the sun", chat=chat, on_step=lambda s: None)
    again = agent.replay(live.log, on_step=lambda s: None)
    assert again.results[0].after["Earth"] == live.results[0].after["Earth"]


def test_a_failing_step_stops_a_replay():
    import pytest

    with pytest.raises(ValueError, match="remove_body failed"):
        agent.replay([{"tool": "remove_body", "args": {"name": "Vulcan"}}], on_step=lambda s: None)
