from run_eval import run_tool, score


def test_bash_runs_in_skill_dir():
    out = run_tool("bash", {"command": "ls SKILL.md"})
    assert out.strip() == "SKILL.md"


def test_read_file_blocks_escape():
    out = run_tool("read_file", {"path": "../../etc/passwd"})
    assert out.startswith("ERROR")


def test_read_file_reads_skill_file():
    assert "wikipedia-interest" in run_tool("read_file", {"path": "SKILL.md"})


def test_score_counts_expectations_and_tool_calls():
    transcript = [{"role": "assistant", "tool_calls": [{"function": {"name": "bash", "arguments": '{"command": "uv run scripts/wiki_interest.py analyze --topic x --langs pl"}'}}]},
                  {"role": "assistant", "content": "Czech per million grew; confidence medium. Polish is missing."}]
    s = score(transcript, ["per million", "confidence", "Polish.*missing"])
    assert s["matched"] == 3 and s["tool_calls"] == 1 and s["used_analyze"] is True


def test_chat_explains_402_and_retries_429(monkeypatch):
    import httpx
    import run_eval

    calls = {"n": 0}

    def fake_post(url, headers, json, timeout):
        calls["n"] += 1
        return httpx.Response(402, json={"error": {"message": "Insufficient credits"}}, request=httpx.Request("POST", url))

    monkeypatch.setattr(run_eval.httpx, "post", fake_post)
    monkeypatch.setattr(run_eval.time, "sleep", lambda s: None)
    try:
        run_eval.chat("m", [], "key")
    except RuntimeError as exc:
        assert "credits" in str(exc).lower() and calls["n"] == 1
    else:
        raise AssertionError("expected RuntimeError")

    def flaky_post(url, headers, json, timeout):
        calls["n"] += 1
        if calls["n"] < 4:
            return httpx.Response(429, json={"error": {"message": "rate-limited"}}, request=httpx.Request("POST", url))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}, request=httpx.Request("POST", url))

    calls["n"] = 0
    monkeypatch.setattr(run_eval.httpx, "post", flaky_post)
    assert run_eval.chat("m", [], "key")["choices"][0]["message"]["content"] == "ok"
    assert calls["n"] == 4


def test_empty_final_answer_gets_one_nudge(monkeypatch):
    import run_eval

    replies = [
        {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": ""}}], "usage": {}},
        {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Final answer here."}}], "usage": {}},
    ]
    seen = []

    def fake_chat(model, messages, api_key):
        seen.append([m.get("role") for m in messages])
        return replies.pop(0)

    monkeypatch.setattr(run_eval, "chat", fake_chat)
    monkeypatch.setattr(run_eval, "system_prompt", lambda: "sys")
    messages, final, usage = run_eval.run_prompt("m", {"prompt": "hi"}, None, 5, "key")
    assert final == "Final answer here."
    assert seen[1][-1] == "user"  # a nudge user message was appended before the retry
    assert any("final answer" in (m.get("content") or "").lower() for m in messages if m.get("role") == "user")
