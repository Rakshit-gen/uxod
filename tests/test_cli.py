import json

from uxod import cli


def test_ask_without_a_key_says_where_to_get_one(monkeypatch, capsys):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert cli.main(["ask", "anything"]) == 2
    assert "console.groq.com" in capsys.readouterr().err


def test_replay_writes_the_page_and_the_plan(tmp_path, capsys):
    plan = tmp_path / "p.json"
    plan.write_text(json.dumps({"question": "no sun", "plan": [
        {"tool": "remove_body", "args": {"name": "Sun"}}, {"tool": "run", "args": {"years": 40}}]}))
    assert cli.main(["replay", str(plan), "-o", str(tmp_path / "out")]) == 0
    assert "Earth left the system" in capsys.readouterr().out
    assert json.loads((tmp_path / "out" / "plan.json").read_text())["question"] == "no sun"
    assert "<canvas" in (tmp_path / "out" / "replay.html").read_text()
