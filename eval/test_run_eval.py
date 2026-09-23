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
