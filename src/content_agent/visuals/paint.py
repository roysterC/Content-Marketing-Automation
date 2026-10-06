"""Paste-ready prompts for painted versions of the single-image visuals.

Roy pastes the prompt into the Gemini app (Nano Banana), which is free there but has no
API, and sends the image back to the Telegram bot.

The prompt has three parts:
- a fixed design system from config/art_style.yaml (art style, font, colours, line
  weight, box style, icons), repeated word for word so every post looks like the same
  designer made it;
- the content as plain data, taken from the same approved copy as the HTML visual, so
  the text in the image is the text that went through review and the fact-check;
- a brief that leaves the layout and composition to Nano Banana, so posts don't all
  look like one template.
"""

import yaml

from content_agent.config import CONFIG_DIR
from content_agent.visuals.render import AUTHOR, TAGLINE

STYLE_FILE = CONFIG_DIR / "art_style.yaml"
DESIGN_KEYS = ("font", "colours", "lines", "boxes", "icons")


def load_styles(path=STYLE_FILE) -> dict:
    return yaml.safe_load(path.read_text())


def style_names(path=STYLE_FILE) -> list[str]:
    return list(load_styles(path)["styles"])


def _q(text: str) -> str:
    """Quote text for the prompt: what the model must render exactly. Curly quotes, so
    copy that has its own straight quotes (DM me "CALLS") stays unambiguous."""
    return f"“{text.strip()}”"


def _design_block(style: str | None) -> tuple[str, str]:
    """The fixed design system for a style, and the style's name."""
    config = load_styles()
    name = style or config["active"]
    if name not in config["styles"]:
        raise ValueError(f"Unknown art style {name!r}; pick one of {', '.join(config['styles'])}")
    s = config["styles"][name]
    design = {**config["design"], **s.get("design", {})}
    lines = [
        f"Art style ({s['name']}): {s['look']}",
        f"Background: {s['background']}",
        *(f"{key.capitalize()}: {design[key]}" for key in DESIGN_KEYS),
    ]
    return "\n".join(lines), config["text_rules"]


def _signature() -> str:
    return f"- Signature, small: {_q(f'{AUTHOR} · {TAGLINE}')}"


def _infographic(idea: dict) -> tuple[str, list[str]]:
    brief = (
        "Show how one everyday job gets automated: the problem, how the fix works step "
        "by step, and what it changes."
    )
    content = [
        f"- Label: {_q(idea.get('eyebrow') or 'Automation idea')}",
        f"- Business type: {_q(idea['sector'])}",
        f"- Headline: {_q(idea['title'])}",
        f"- The problem: {_q(idea['problem'])}",
        f"- How it works, {len(idea['steps'])} steps in this order (title / one line):",
        *(f"  {i}. {_q(s['title'])} / {_q(s['detail'])}" for i, s in enumerate(idea["steps"], 1)),
        f"- Results, {len(idea['impact'])} figures (number / label):",
        *(f"  - {_q(s['value'])} / {_q(s['label'])}" for s in idea["impact"]),
        f"- Note on the figures, small: {_q(idea['impact_note'])}",
        f"- Call to action: {_q(idea['cta'])}",
        _signature(),
        (
            f"- Optional section headings: {_q('The problem')}, {_q('How it works')}, "
            f"{_q('The result')}"
        ),
    ]
    if idea.get("scene"):
        content.append(f"- Illustration idea (optional, adapt or replace): {idea['scene']}")
    return brief, content


def _orgchart(chart: dict) -> tuple[str, list[str]]:
    title = f"{chart['title_before']}{chart['title_accent']}{chart['title_after']}".strip()
    brief = (
        "Show the business's everyday jobs as a team of automated staff: the business at "
        "the top, the automations grouped by department beneath it, like a staff chart."
    )
    content = [
        f"- Headline: {_q(title)}, with {_q(chart['title_accent'])} highlighted",
        f"- Subtitle: {_q(chart['subtitle'])}",
        f"- At the top: {_q(chart['root_label'])} / {_q(chart['root_name'])}",
        (
            f"- {len(chart['departments'])} departments, each with its automations "
            "(name / nickname / what it does):"
        ),
    ]
    for i, dept in enumerate(chart["departments"], 1):
        content.append(f"  {i}. {_q(dept['name'])}")
        content += [
            f"     - {_q(r['name'])} / {_q(r['nickname'])} / {_q(r['does'])}" for r in dept["roles"]
        ]
    content += [f"- Call to action: {_q(chart['cta'])}", _signature()]
    return brief, content


CONTENT = {"infographic": _infographic, "orgchart": _orgchart}


def build_prompt(kind: str, data: dict, style: str | None = None) -> str:
    """The full Gemini prompt for a visual. `kind` is the format's visual key
    ("infographic" or "orgchart"); `style` defaults to the active art style."""
    design, text_rules = _design_block(style)
    brief, content = CONTENT[kind](data)
    return f"""\
Design a professional, eye-catching social media infographic for small-business owners
on LinkedIn and Facebook. Portrait, 4:5 aspect ratio (1080 × 1350). {brief}

YOUR CREATIVE FREEDOM
You choose the layout, composition, hierarchy and how to show the information: a flow,
path, timeline, scene with callouts, cards, before and after, or anything else that tells
it clearly. Make it distinctive, not a template. It must read easily on a phone: a clear
focal point, standout headline and numbers, steps in order, comfortable margins, and the
signature small at the bottom.

FIXED DESIGN SYSTEM (identical on every post, follow it exactly)
{design}

CONTENT
{text_rules}
{chr(10).join(content)}

If I attach a reference image, match its art style, font, colours, line weight and box
style exactly, but design your own layout for this content."""
