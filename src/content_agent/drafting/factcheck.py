"""Second-pass check that drafts don't state anything the source doesn't support.

Runs as a separate call so the checker isn't marking its own homework. Results are
attached to the draft and shown in the approval message; nothing is auto-rejected.
"""

import json

from content_agent.llm import ask_json

SYSTEM = """\
You are a strict fact-checker for social media drafts written for a small-business audience.

You get the SOURCE material and the DRAFTS (LinkedIn post, Facebook post, carousel slides).
Flag every statement in the drafts that is presented as fact but is not supported by the
source, in particular:
- statistics, percentages, prices, time or money saved
- named clients, case studies, testimonials or results
- claims about what an AI product, model or company has released or can do
- dates and version numbers

Do NOT flag: opinions, general advice, clearly-labelled hypothetical examples
("if you miss 5 calls a day..."), or widely known common sense.

verdict is "pass" when nothing needs attention, otherwise "needs_attention".
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "needs_attention"]},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "problem": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": ["claim", "problem", "suggestion"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["verdict", "issues"],
    "additionalProperties": False,
}


def factcheck(drafts: dict, source_text: str) -> dict:
    prompt = (
        f"<source>\n{source_text}\n</source>\n\n"
        f"<drafts>\n{json.dumps(drafts, indent=2, ensure_ascii=False)}\n</drafts>"
    )
    return ask_json(system=SYSTEM, prompt=prompt, schema=SCHEMA, effort="high")
