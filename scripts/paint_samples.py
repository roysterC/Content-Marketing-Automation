"""Write docs/painted-style-samples.md: one test infographic as a Gemini prompt in every
art style from config/art_style.yaml, to compare the looks side by side.

    python scripts/paint_samples.py
"""

from pathlib import Path

from content_agent.visuals import paint

OUT = Path(__file__).resolve().parents[1] / "docs" / "painted-style-samples.md"

# Test content only (illustrative numbers): it exists to compare styles, not to post.
IDEA = {
    "eyebrow": "Automation idea",
    "sector": "Nail salons",
    "title": "Turn missed calls into bookings",
    "problem": "You're mid-manicure, the phone rings, and by the time you're free the "
    "caller has booked somewhere else.",
    "steps": [
        {"icon": "missed-call", "title": "Call goes unanswered",
         "detail": "Your phone line spots the missed call, even mid-appointment."},
        {"icon": "message", "title": "Instant text back",
         "detail": "The caller gets a friendly text with your booking link."},
        {"icon": "calendar", "title": "They pick a slot",
         "detail": "They book a free time without waiting for you."},
        {"icon": "bell", "title": "Reminder the day before",
         "detail": "An automatic reminder cuts no-shows."},
    ],
    "impact": [
        {"icon": "clock", "value": "~2 hrs", "label": "less time on the phone a week"},
        {"icon": "check", "value": "24/7", "label": "every caller gets a reply"},
        {"icon": "users", "value": "0", "label": "callers left hanging"},
    ],
    "impact_note": "Illustrative estimates for a typical salon",
    "scene": "a nail technician mid-manicure while the salon phone rings unanswered on the "
    "front desk",
    "cta": 'DM me "CALLS" to see it working',
}  # fmt: skip

HEADER = """\
# Painted style samples

Paste-ready Gemini (Nano Banana) prompts for the same test infographic in each art style
from `config/art_style.yaml`, so you can compare the looks before picking one. The
content is test content (illustrative numbers), not a post.

How to try one: open the Gemini app, choose image creation (🍌), paste a prompt and send.
Run each one twice to see how consistent the style is. When you've picked a style, set
`active:` in `config/art_style.yaml`, and keep your favourite image to attach as a style
reference with future prompts.

Regenerate this file after editing the styles: `python scripts/paint_samples.py`.
"""


def main() -> None:
    styles = paint.load_styles()["styles"]
    sections = [
        f"## {styles[name]['name']} (`{name}`)\n\n"
        f"```text\n{paint.build_prompt('infographic', IDEA, name)}\n```\n"
        for name in styles
    ]
    OUT.write_text("\n".join([HEADER, *sections]))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
