#!/usr/bin/env python3
"""Run the task's example prompts against a cheap model via OpenRouter with the skill installed.

Usage: uv run run_eval.py --model anthropic/claude-haiku-4.5 [--prompt-id 1-if-pl-cs] [--max-turns 15]
Writes transcripts to eval/transcripts/<model>/ and appends a rubric row to eval/RESULTS.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SKILL_DIR = REPO / "wikipedia-interest"
load_dotenv(REPO / ".env")

TOOLS = [
    {"type": "function", "function": {
        "name": "bash",
        "description": "Run a shell command inside the skill directory (cwd = skill root). Output truncated to 8000 chars.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a text file inside the skill directory by relative path.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
]


def system_prompt() -> str:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    return ("You are an analyst agent helping a B2C product founder. Answer in the user's language. "
            "You have two tools: bash (runs in the skill directory) and read_file. The following skill is installed "
            "and its working directory is your bash cwd:\n\n" + skill)


def run_tool(name: str, args: dict) -> str:
    if name == "bash":
        try:
            p = subprocess.run(args["command"], shell=True, cwd=SKILL_DIR, capture_output=True, text=True, timeout=240)
        except subprocess.TimeoutExpired:
            return "ERROR: command timed out after 240 s"
        out = (p.stdout + ("\n[stderr]\n" + p.stderr if p.stderr.strip() else "")).strip()
        out = out or f"(no output, exit {p.returncode})"
        return out[:8000] + ("\n…[truncated]" if len(out) > 8000 else "")
    if name == "read_file":
        target = (SKILL_DIR / args["path"]).resolve()
        if SKILL_DIR not in target.parents and target != SKILL_DIR:
            return "ERROR: path escapes the skill directory"
        if not target.exists():
            return f"ERROR: {args['path']} not found"
        text = target.read_text(encoding="utf-8", errors="replace")
        return text[:12000] + ("\n…[truncated]" if len(text) > 12000 else "")
    return f"ERROR: unknown tool {name}"


def chat(model: str, messages: list[dict], api_key: str) -> dict:
    r = None
    for attempt in range(4):
        r = httpx.post("https://openrouter.ai/api/v1/chat/completions",
                       headers={"Authorization": f"Bearer {api_key}",
                                "HTTP-Referer": "https://github.com/vampir/genesisAiEngineerCourse",
                                "X-Title": "wikipedia-interest skill eval"},
                       json={"model": model, "messages": messages, "tools": TOOLS, "temperature": 0}, timeout=180)
        if r.status_code in (429, 500, 502, 503):
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"OpenRouter error: {data['error']}")
        return data
    raise RuntimeError(f"OpenRouter kept failing: {r.status_code} {r.text[:300]}")


def run_prompt(model: str, prompt: dict, prior: list[dict] | None, max_turns: int, api_key: str) -> tuple[list[dict], str, dict]:
    messages = prior[:] if prior else [{"role": "system", "content": system_prompt()}]
    messages.append({"role": "user", "content": prompt["prompt"]})
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0}
    final = ""
    for _ in range(max_turns):
        resp = chat(model, messages, api_key)
        usage = resp.get("usage", {})
        for k in usage_total:
            usage_total[k] += usage.get(k, 0) or 0
        msg = resp["choices"][0]["message"]
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            final = msg.get("content") or ""
            break
        for call in calls:
            fn = call["function"]
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            result = run_tool(fn["name"], args)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
    return messages, final, usage_total


def score(messages: list[dict], expectations: list[str]) -> dict:
    final = next((m.get("content") or "" for m in reversed(messages)
                  if m.get("role") == "assistant" and not m.get("tool_calls")), "")
    calls = [c for m in messages if m.get("role") == "assistant" for c in (m.get("tool_calls") or [])]
    cmds = []
    for c in calls:
        if c["function"]["name"] == "bash":
            try:
                cmds.append(json.loads(c["function"]["arguments"]).get("command", ""))
            except json.JSONDecodeError:
                cmds.append("")
    matched = sum(1 for e in expectations if re.search(e, final, re.I | re.S))
    return {
        "matched": matched, "expected": len(expectations), "tool_calls": len(calls),
        "used_resolve": any(" resolve " in c for c in cmds),
        "used_analyze": any(" analyze " in c for c in cmds),
        "used_report": any(" report " in c for c in cmds),
        "final_chars": len(final),
    }


def write_transcript(path: Path, messages: list[dict], usage: dict, sc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_suffix(".raw.json").write_text(json.dumps(messages, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# Transcript — {path.stem}", f"usage: {usage}", f"score: {sc}", ""]
    for m in messages:
        role = m.get("role")
        if role == "system":
            lines.append("## system\n(SKILL.md as system prompt — omitted)\n")
        elif role == "user":
            lines.append(f"## user\n{m['content']}\n")
        elif role == "assistant":
            if m.get("tool_calls"):
                for c in m["tool_calls"]:
                    try:
                        shown = json.loads(c["function"]["arguments"]).get("command") or c["function"]["arguments"]
                    except json.JSONDecodeError:
                        shown = c["function"]["arguments"]
                    lines.append(f"## assistant → {c['function']['name']}\n```\n{shown}\n```\n")
            if m.get("content"):
                lines.append(f"## assistant\n{m['content']}\n")
        elif role == "tool":
            lines.append(f"## tool result\n```\n{m['content'][:3000]}\n```\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt-id")
    ap.add_argument("--max-turns", type=int, default=15)
    args = ap.parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY missing (put it in .env at repo root)")
        return 3
    prompts = json.loads((HERE / "prompts.json").read_text(encoding="utf-8"))
    if args.prompt_id:
        prompts = [p for p in prompts if p["id"] == args.prompt_id or p.get("after") == args.prompt_id]
    histories: dict[str, list[dict]] = {}
    rows = []
    for p in prompts:
        prior = histories.get(p["after"]) if p.get("after") else None
        if p.get("after") and prior is None:
            print(f"skip {p['id']}: depends on {p['after']} which did not run")
            continue
        t0 = time.time()
        messages, final, usage = run_prompt(args.model, p, prior, args.max_turns, api_key)
        histories[p["id"]] = messages
        sc = score(messages, p["expect"])
        slug = re.sub(r"[^a-z0-9]+", "-", args.model.lower())
        write_transcript(HERE / "transcripts" / slug / f"{p['id']}.md", messages, usage, sc)
        rows.append(f"| {datetime.now(timezone.utc):%Y-%m-%d} | `{args.model}` | {p['id']} | {sc['matched']}/{sc['expected']} | "
                    f"{sc['tool_calls']} | {'✓' if sc['used_resolve'] else '–'} | {'✓' if sc['used_analyze'] else '–'} | "
                    f"{'✓' if sc['used_report'] else '–'} | {usage['prompt_tokens']}+{usage['completion_tokens']} | "
                    f"{time.time() - t0:.0f}s |")
        print(rows[-1])
    results = HERE / "RESULTS.md"
    if not results.exists():
        results.write_text("# Eval results\n\n| date | model | prompt | expectations | tool calls | resolve | analyze | report "
                           "| tokens in+out | wall |\n|---|---|---|---|---|---|---|---|---|---|\n", encoding="utf-8")
    with results.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(rows) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
