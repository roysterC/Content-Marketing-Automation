"""Thin wrapper around the Claude API: structured JSON out, cached system prompt."""

import json
import logging
from functools import lru_cache

import anthropic

from content_agent.config import get_settings

log = logging.getLogger(__name__)

# Server-side refusal fallback: if a safety classifier declines a request, the API
# re-runs it on Anthropic's recommended fallback model instead of returning a refusal.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    pass


@lru_cache
def client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def ask_json(
    *,
    system: str,
    prompt: str,
    schema: dict,
    effort: str = "medium",
    max_tokens: int = 16000,
) -> dict:
    """Send one request and return the JSON object Claude produced.

    `system` is marked cacheable: keep it stable across calls (brand voice, examples,
    instructions) and put anything that varies in `prompt`, so repeated runs only pay
    full price for the variable part.
    """
    response = client().beta.messages.create(
        model=get_settings().claude_model,
        max_tokens=max_tokens,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}],
        output_config={
            "effort": effort,
            "format": {"type": "json_schema", "schema": schema},
        },
    )
    usage = response.usage
    log.info(
        "claude %s: in=%s cached=%s out=%s",
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
