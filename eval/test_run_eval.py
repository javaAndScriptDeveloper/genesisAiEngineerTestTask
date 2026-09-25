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


def test_claude_events_become_openai_shaped_messages():
    from run_eval import claude_events_to_messages, score
    events = [
        {"type": "system", "subtype": "init", "session_id": "s1"},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "uv run scripts/wiki_interest.py analyze --topic x --langs cs", "description": "run"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "# x — cs\n| topic |"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Czech: 2 per million, confidence high."}]}},
        {"type": "result", "result": "Czech: 2 per million, confidence high.", "session_id": "s1", "total_cost_usd": 0.01,
         "usage": {"input_tokens": 5, "output_tokens": 7, "cache_read_input_tokens": 100}},
    ]
    messages, meta = claude_events_to_messages(events)
    roles = [m["role"] for m in messages]
    assert roles == ["assistant", "tool", "assistant"]
    assert messages[0]["tool_calls"][0]["function"]["name"] == "bash"
    assert "analyze" in messages[0]["tool_calls"][0]["function"]["arguments"]
    assert messages[1]["content"].startswith("# x")
    assert messages[2]["content"] == "Czech: 2 per million, confidence high."
    assert meta["session_id"] == "s1" and meta["cost_usd"] == 0.01
    assert meta["usage"] == {"prompt_tokens": 105, "completion_tokens": 7}
    s = score(messages, ["per million", "confidence"])
    assert s["matched"] == 2 and s["tool_calls"] == 1 and s["used_analyze"]


def test_claude_events_map_read_and_other_tools():
    from run_eval import claude_events_to_messages
    events = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "/x/SKILL.md"}},
            {"type": "tool_use", "id": "t2", "name": "Skill", "input": {"skill": "wikipedia-interest"}}]}},
        {"type": "result", "result": "", "session_id": "s", "usage": {}},
    ]
    messages, _ = claude_events_to_messages(events)
    names = [c["function"]["name"] for c in messages[0]["tool_calls"]]
    assert names == ["read_file", "Skill"]


def test_claude_cmd_builds_resumable_command(tmp_path):
    from run_eval import claude_cmd
    cmd = claude_cmd("haiku", "hello", resume=None)
    assert cmd[:2] == ["claude", "-p"] and "hello" in cmd and "--model" in cmd and "haiku" in cmd
    assert "--output-format" in cmd and "stream-json" in cmd and "--permission-mode" in cmd
    assert "--resume" not in cmd
    cmd2 = claude_cmd("haiku", "more", resume="abc")
    assert cmd2[cmd2.index("--resume") + 1] == "abc"
