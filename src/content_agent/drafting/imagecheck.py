"""Proofread a painted image against the prompt it was made from.

Image models draw text letter by letter and sometimes get it wrong, or add words and
numbers nobody asked for. The prompt's quoted text is the approved, fact-checked copy, so
Claude compares what the image actually says with it. Nothing is blocked: the result
goes to Roy in Telegram, like the fact-check.
"""

import logging
import tempfile
from pathlib import Path

from PIL import Image

from content_agent.llm import ask_json

log = logging.getLogger(__name__)

# Claude sees images at up to about this many pixels on the long edge; anything bigger
# only costs upload size and tokens.
MAX_EDGE = 1568

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["ok", "needs_attention"]},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text as it appears in the image",
                    },
                    "problem": {"type": "string", "description": "What's wrong, briefly"},
                },
                "required": ["text", "problem"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["verdict", "issues"],
    "additionalProperties": False,
}

SYSTEM = """\
You proofread AI-generated social media infographics before a small-business owner posts
them. You get the image and the prompt it was generated from. Every piece of text in
“curly quotes” in the prompt is approved copy that must appear in the image exactly once
(without the curly quotes themselves).

Report, as issues:
- misspelt, garbled, cut-off or unreadable words
- quoted text that is missing or changed (including numbers, symbols and capitals)
- any extra words, numbers, statistics, claims, logos or signatures that are not in the
  quoted text (including text painted onto objects or signs)
- text that is duplicated

Ignore the art style, colours and layout details unless they make text unreadable.
Verdict "ok" only when there are no issues."""


def _shrunk(image: Path, out_dir: Path) -> Path:
    """A JPEG copy no bigger than Claude needs (also converts PNG/WebP with alpha)."""
    with Image.open(image) as im:
        im = im.convert("RGB")
        im.thumbnail((MAX_EDGE, MAX_EDGE))
        out = out_dir / "check.jpg"
        im.save(out, "JPEG", quality=90)
    return out


def check_image(image: Path, prompt: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="content-agent-check-") as tmp:
        result = ask_json(
            system=SYSTEM,
            prompt=f"The prompt the image was made from:\n\n{prompt}",
            schema=SCHEMA,
            effort="medium",
            images=[_shrunk(image, Path(tmp))],
        )
    log.info("Image check: %s (%d issues)", result["verdict"], len(result["issues"]))
    return result


def format_check(result: dict) -> str:
    if result["verdict"] == "ok" and not result["issues"]:
        return "✅ Text check passed: every word and number matches the approved copy."
    lines = ["⚠️ Text check found problems. Regenerate in Gemini, or use it anyway:"]
    lines += [f"• {i['text']}: {i['problem']}" for i in result["issues"]]
    return "\n".join(lines)
