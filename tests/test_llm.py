"""claude_code backend, with the CLI subprocess faked out."""

import json
import subprocess

import pytest

from content_agent import llm

SCHEMA = {"type": "object", "properties": {"score": {"type": "integer"}}, "required": ["score"]}


def _fake_run(stdout: dict | str, returncode: int = 0, seen: dict | None = None):
    def run(cmd, **kwargs):
        if seen is not None:
            seen.update(cmd=cmd, **kwargs)
        out = stdout if isinstance(stdout, str) else json.dumps(stdout)
        return subprocess.CompletedProcess(cmd, returncode, stdout=out, stderr="")

    return run


def test_returns_structured_output_and_hides_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-leak")
    seen: dict = {}
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_run({"is_error": False, "structured_output": {"score": 8}}, seen=seen),
    )

    result = llm.ask_json(system="sys", prompt="hello", schema=SCHEMA, effort="low")

    assert result == {"score": 8}
    assert "ANTHROPIC_API_KEY" not in seen["env"]
    assert seen["input"] == "hello"
    cmd = seen["cmd"]
    assert cmd[cmd.index("--tools") + 1] == ""
    assert cmd[cmd.index("--effort") + 1] == "low"
    assert json.loads(cmd[cmd.index("--json-schema") + 1]) == SCHEMA


def test_oauth_token_from_settings_reaches_cli(monkeypatch):
    settings = llm.get_settings().model_copy(update={"claude_code_oauth_token": "tok-123"})
    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    seen: dict = {}
    monkeypatch.setattr(
        subprocess, "run", _fake_run({"is_error": False, "structured_output": {}}, seen=seen)
    )
    llm.ask_json(system="s", prompt="p", schema=SCHEMA)
    assert seen["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "tok-123"


def test_error_result_raises(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_run({"is_error": True, "subtype": "error", "result": "Not logged in"}, 1),
    )
    with pytest.raises(llm.LLMError, match="Not logged in"):
        llm.ask_json(system="s", prompt="p", schema=SCHEMA)


def test_non_json_output_raises(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run("boom", 2))
    with pytest.raises(llm.LLMError, match="exited 2"):
        llm.ask_json(system="s", prompt="p", schema=SCHEMA)
