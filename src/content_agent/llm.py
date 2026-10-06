"""Get a JSON answer from Claude, via your Pro/Max plan or the API.

Two backends, chosen by LLM_BACKEND:

- claude_code (default): runs `claude -p` (Claude Code in headless mode), which
  authenticates with your Claude subscription. No API key, no per-token bill; usage
  counts against the same plan limits as your interactive Claude use.
- api: calls the Claude API with ANTHROPIC_API_KEY. Pay per token, but separate rate
  limits and access to API-only features (server-side refusal fallback, cache control).
"""

import base64
import json
import logging
import os
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from content_agent.config import get_settings

log = logging.getLogger(__name__)

CLI_TIMEOUT_SECONDS = 600

# Server-side refusal fallback (API backend only): if a safety classifier declines a
# request, the API re-runs it on Anthropic's recommended fallback model.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    pass


def ask_json(
    *,
    system: str,
    prompt: str,
    schema: dict,
    effort: str = "medium",
    max_tokens: int = 16000,
    web: bool = False,
    images: list[Path] | None = None,
) -> dict:
    """Send one request and return the JSON object Claude produced.

    Keep `system` stable across calls (brand voice, examples, instructions) and put
    anything that varies in `prompt`, so repeated runs can reuse the prompt cache.

    web=True lets Claude search and read web pages before answering (claude_code
    backend only; the api backend answers from Claude's own knowledge).

    images: PNG, JPEG or WebP files for Claude to look at alongside the prompt.
    """
    images = images or []
    if get_settings().llm_backend == "api":
        return _ask_api(system, prompt, schema, effort, max_tokens, images)
    return _ask_claude_code(system, prompt, schema, effort, web, images)


# --- claude_code backend ---


WEB_TOOLS = "WebSearch,WebFetch"
READ_TOOL = "Read"


def claude_code_command(
    schema: dict, system_file: Path, effort: str, web: bool = False, read: bool = False
) -> list[str]:
    s = get_settings()
    # Text-in/JSON-out by default: no file, shell, web or MCP tools. With web=True,
    # only web search/fetch are enabled; with read=True, only Read (to look at images
    # copied into the call's temporary directory). Enabled tools are pre-approved,
    # since nobody is there to answer a permission prompt.
    enabled = ",".join(t for t, on in ((WEB_TOOLS, web), (READ_TOOL, read)) if on)
    tools = ["--tools", enabled, "--allowedTools", enabled] if enabled else ["--tools", ""]
    return [
        s.claude_cli,
        "-p",
        "--output-format", "json",
        "--json-schema", json.dumps(schema),
        "--system-prompt-file", str(system_file),
        "--model", s.claude_model,
        "--effort", effort,
        *tools,
        "--disallowedTools", "mcp__*",
        "--no-session-persistence",
    ]  # fmt: skip


def _ask_claude_code(
    system: str, prompt: str, schema: dict, effort: str, web: bool, images: list[Path]
) -> dict:
    # ANTHROPIC_API_KEY outranks the subscription login in `claude -p`, so drop it to
    # make sure this backend really runs on the plan.
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    if token := get_settings().claude_code_oauth_token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token  # read from .env, which the CLI doesn't see

    # Run from an empty directory so Claude Code doesn't load this repo's CLAUDE.md
    # or project settings into every call.
    with tempfile.TemporaryDirectory(prefix="content-agent-") as tmp:
        system_file = Path(tmp) / "system.md"
        system_file.write_text(system)
        if images:
            copies = []
            for i, image in enumerate(images, 1):
                copy = Path(tmp) / f"image-{i}{image.suffix.lower()}"
                shutil.copyfile(image, copy)
                copies.append(str(copy))
            prompt += "\n\nImages (open each with the Read tool):\n" + "\n".join(copies)
        try:
            proc = subprocess.run(
                claude_code_command(schema, system_file, effort, web, read=bool(images)),
                input=prompt,
                capture_output=True,
                text=True,
                cwd=tmp,
                env=env,
                timeout=CLI_TIMEOUT_SECONDS,
                check=False,  # the JSON result carries the error detail
            )
        except FileNotFoundError as e:
            raise LLMError(
                "Claude Code CLI not found. Install it and log in, or set LLM_BACKEND=api"
            ) from e

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise LLMError(f"claude exited {proc.returncode}: {proc.stderr or proc.stdout}") from e

    if result.get("is_error") or proc.returncode != 0:
        raise LLMError(f"claude failed ({result.get('subtype')}): {result.get('result')}")
    if result.get("structured_output") is None:
        raise LLMError(f"claude returned no structured output: {result.get('result')}")

    usage = result.get("usage", {})
    log.info(
        "claude-code %s: in=%s cached=%s out=%s",
        get_settings().claude_model,
        usage.get("input_tokens"),
        usage.get("cache_read_input_tokens"),
        usage.get("output_tokens"),
    )
    return result["structured_output"]


# --- api backend ---


@lru_cache
def _client():
    import anthropic

    return anthropic.Anthropic()


MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def _image_block(path: Path) -> dict:
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    media_type = MEDIA_TYPES[path.suffix.lower()]
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}


def _ask_api(
    system: str, prompt: str, schema: dict, effort: str, max_tokens: int, images: list[Path]
) -> dict:
    content = [*(_image_block(p) for p in images), {"type": "text", "text": prompt}]
    response = _client().beta.messages.create(
        model=get_settings().claude_model,
        max_tokens=max_tokens,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": content}],
        output_config={
            "effort": effort,
            "format": {"type": "json_schema", "schema": schema},
        },
    )
    usage = response.usage
    log.info(
        "claude-api %s: in=%s cached=%s out=%s",
        response.model,
        usage.input_tokens,
        usage.cache_read_input_tokens,
        usage.output_tokens,
    )
    if response.stop_reason == "refusal":
        raise LLMError(f"Request declined: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise LLMError("Response hit max_tokens; raise the limit for this call")

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
