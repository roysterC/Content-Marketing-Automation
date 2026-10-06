"""Paste-ready prompts for painted versions of the single-image visuals.

Roy pastes the prompt into the Gemini app (Nano Banana), which is free there but has no
API, and sends the image back to the Telegram bot. The prompt is built from the same
approved content as the HTML visual, so the text in the image is the text that went
through review and the fact-check. The art style comes from config/art_style.yaml and is
repeated word for word in every prompt, so every post looks like the same illustrator.
"""

import yaml

from content_agent.config import CONFIG_DIR
from content_agent.visuals.render import AUTHOR, TAGLINE

STYLE_FILE = CONFIG_DIR / "art_style.yaml"

# What to paint for each line-icon name: Claude already picks an icon per step, role and
# outcome, so the painted image reuses that choice as a small illustrated vignette.
VIGNETTES = {
    "phone": "a ringing phone",
    "missed-call": "a phone showing a missed call",
    "message": "a text message bubble",
    "calendar": "an open booking diary",
    "clock": "a clock",
    "bell": "a reminder bell",
    "check": "a big tick",
    "cross": "a cross",
    "user": "a client",
    "users": "a small group of people",
    "pound": "a stack of pound coins",
    "star": "a five-star review",
    "mail": "an envelope",
    "zap": "a lightning bolt",
    "trending-up": "a rising line chart",
    "repeat": "two circular arrows",
    "shield": "a shield with a tick",
    "search": "a magnifying glass",
    "document": "a sheet of paper",
    "settings": "a cog",
    "chart": "a bar chart",
    "target": "a target",
    "heart": "a heart",
    "lightbulb": "a lightbulb",
    "hourglass": "an hourglass",
    "inbox": "an inbox tray",
    "link": "two linked chain rings",
    "arrow-right": "an arrow pointing forward",
    "robot": "a friendly little robot",
}


def load_styles(path=STYLE_FILE) -> dict:
    return yaml.safe_load(path.read_text())


def style_names(path=STYLE_FILE) -> list[str]:
    return list(load_styles(path)["styles"])


def vignette(icon: str) -> str:
    return VIGNETTES.get(icon, icon.replace("-", " ") if icon else "a simple object")


def _q(text: str) -> str:
    """Quote text for the prompt: what the model must render exactly. Curly quotes, so
    copy that has its own straight quotes (DM me "CALLS") stays unambiguous."""
    return f"“{text.strip()}”"


def _style_block(style: str | None) -> str:
    config = load_styles()
    name = style or config["active"]
    if name not in config["styles"]:
        raise ValueError(f"Unknown art style {name!r}; pick one of {', '.join(config['styles'])}")
    s = config["styles"][name]
    return f"""\
ART STYLE ({s["name"]})
{s["look"]}
Background: {s["background"]}
Colours: {config["palette"]}

TEXT
{config["typography"]}
{config["text_rules"]}"""


def _footer(cta: str) -> str:
    return (
        f"Footer strip under a thin divider: {_q(f'{AUTHOR} · {TAGLINE}')} on the left, "
        f"{_q(cta)} in amber on the right."
    )


def _infographic_layout(idea: dict) -> str:
    eyebrow = (idea.get("eyebrow") or "Automation idea").upper()
    steps = "\n".join(
        f"   {i}. {_q(s['title'])} / {_q(s['detail'])} (vignette: {vignette(s['icon'])})"
        for i, s in enumerate(idea["steps"], 1)
    )
    impact = "\n".join(
        f"   - {_q(s['value'])} / {_q(s['label'])} (vignette: {vignette(s['icon'])})"
        for s in idea["impact"]
    )
    scene = idea.get("scene") or f"a typical day at a busy {idea['sector'].lower()} business"
    return f"""\
LAYOUT, top to bottom
1. Small amber label {_q(eyebrow)} beside a rounded pill {_q(idea["sector"])}.
2. Headline, the largest text, in cream: {_q(idea["title"])}
3. Full-width painted hero illustration, about a quarter of the height: {scene}.
   No text or signs in it.
4. Slim panel with an amber left edge: {_q("The problem:")} in bold, then
   {_q(idea["problem"])}
5. Small muted label {_q("HOW IT WORKS")}, then {len(idea["steps"])} steps in a vertical
   flow joined by a painted amber line. Each has a round amber number badge with a small
   painted vignette, a bold title and one plain line (title / line):
{steps}
6. A row of {len(idea["impact"])} equal cards, each a big amber number with a short label
   under it (number / label):
{impact}
7. Small muted note under the cards: {_q(idea["impact_note"])}
8. {_footer(idea["cta"])}"""


def _orgchart_layout(chart: dict) -> str:
    title = f"{chart['title_before']}{chart['title_accent']}{chart['title_after']}".strip()
    columns = []
    for i, dept in enumerate(chart["departments"], 1):
        cards = "\n".join(
            f"      - {_q(r['name'])} / {_q(r['nickname'])} / {_q(r['does'])}"
            for r in dept["roles"]
        )
        columns.append(f"   {i}. {_q(dept['name'])} (vignette: {vignette(dept['icon'])})\n{cards}")
    return f"""\
LAYOUT, an org chart, top to bottom
1. Headline, the largest text: {_q(title)}, with the words {_q(chart["title_accent"])}
   in amber and the rest in cream.
2. Muted subtitle: {_q(chart["subtitle"])}
3. Root card centred near the top: tiny amber label {_q(chart["root_label"])}, the name
   {_q(chart["root_name"])} in bold and a painted vignette of {vignette(chart["root_icon"])}.
4. Painted dashed lines from the root to {len(chart["departments"])} department columns
   side by side, each in its own tint of the palette, with a small painted vignette and
   its name on top. Under it, stacked cards of three lines each: automation name (bold,
   cream) / nickname (amber) / what it does (small, muted):
{chr(10).join(columns)}
5. {_footer(chart["cta"])}"""


LAYOUTS = {"infographic": _infographic_layout, "orgchart": _orgchart_layout}


def build_prompt(kind: str, data: dict, style: str | None = None) -> str:
    """The full Gemini prompt for a visual. `kind` is the format's visual key
    ("infographic" or "orgchart"); `style` defaults to the active art style."""
    return f"""\
Create a finished, professional social media infographic. Portrait, 4:5 aspect ratio
(1080 × 1350), with everything fitting inside comfortable margins.

{_style_block(style)}

{LAYOUTS[kind](data)}

If I attach a reference image, match its art style, colours and finish exactly, but use
the layout and text above."""
