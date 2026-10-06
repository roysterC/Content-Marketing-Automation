"""JSON schemas for the single-image visuals, next to the templates that render them.

Claude fills these; visuals/templates/idea.html renders INFOGRAPHIC and orgchart.html
renders ORGCHART. Word limits in the descriptions keep text readable at full size.
"""

from content_agent.visuals.icons import ICON_NAMES


def _str(desc: str) -> dict:
    return {"type": "string", "description": desc}


ICON = {"type": "string", "enum": ICON_NAMES}

INFOGRAPHIC = {
    "type": "object",
    "properties": {
        "eyebrow": _str(
            "Small label above the title, 1-3 words, e.g. 'Automation idea', 'Industry "
            "problem', 'Case study', 'Free guide'"
        ),
        "sector": _str("Business type as shown on the graphic, title case, e.g. 'Nail salons'"),
        "title": _str(
            "The idea as an outcome, max ~9 words, e.g. 'Turn missed calls into bookings'"
        ),
        "problem": _str("The pain in the owner's words, 1-2 sentences, max ~30 words"),
        "steps": {
            "type": "array",
            "description": "3-5 steps of how the automation works, in order",
            "items": {
                "type": "object",
                "properties": {
                    "icon": ICON,
                    "title": _str("Max ~5 words"),
                    "detail": _str("One plain sentence, max ~14 words"),
                },
                "required": ["icon", "title", "detail"],
                "additionalProperties": False,
            },
        },
        "impact": {
            "type": "array",
            "description": "2-3 outcomes. Short value (e.g. '~2 hrs', '24/7', '0') and label",
            "items": {
                "type": "object",
                "properties": {
                    "icon": ICON,
                    "value": _str("Max ~7 characters"),
                    "label": _str("Max ~6 words"),
                },
                "required": ["icon", "value", "label"],
                "additionalProperties": False,
            },
        },
        "impact_note": _str("One short line saying the figures are illustrative estimates"),
        "scene": _str(
            "For the painted version: one sentence suggesting an illustration of this "
            "business and moment, e.g. 'a nail technician mid-manicure while the salon phone "
            "rings unanswered on the front desk'. Concrete, no text or signs in it; the image "
            "model may adapt it"
        ),
        "cta": _str("Short call to action, max ~7 words, e.g. 'DM me \"CALLS\" to see it working'"),
    },
    "required": [
        "eyebrow",
        "sector",
        "title",
        "problem",
        "steps",
        "impact",
        "impact_note",
        "scene",
        "cta",
    ],
    "additionalProperties": False,
}

ORGCHART = {
    "type": "object",
    "properties": {
        "title_before": _str("Headline text before the accent word(s), e.g. \"Your Salon's \""),
        "title_accent": _str("1-2 accent-coloured words, e.g. 'AI Team'"),
        "title_after": _str("Headline text after the accent, often ''"),
        "subtitle": _str("One line with the count, e.g. '12 automations, organised like real staff'"),
        "root_label": _str("Tiny label above the root, e.g. 'The owner'"),
        "root_name": _str("Root box name, e.g. 'Your salon' (max ~3 words)"),
        "root_icon": ICON,
        "departments": {
            "type": "array",
            "description": "4 departments (3-5 allowed), each a real area of the business",
            "items": {
                "type": "object",
                "properties": {
                    "name": _str("1-2 words, e.g. 'Front desk'"),
                    "icon": ICON,
                    "roles": {
                        "type": "array",
                        "description": "3 automations (2-4 allowed); same count in every department",
                        "items": {
                            "type": "object",
                            "properties": {
                                "icon": ICON,
                                "name": _str("The automation, 1-3 words, e.g. 'Reminders'"),
                                "nickname": _str("A friendly job title, 1-3 words, e.g. 'No-Show Guard'"),
                                "does": _str("What it does, 3-6 plain words"),
                            },
                            "required": ["icon", "name", "nickname", "does"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["name", "icon", "roles"],
                "additionalProperties": False,
            },
        },
        "cta": _str("Short call to action, max ~7 words, e.g. 'DM me \"TEAM\" for the full breakdown'"),
    },
    "required": [
        "title_before", "title_accent", "title_after", "subtitle", "root_label",
        "root_name", "root_icon", "departments", "cta",
    ],
    "additionalProperties": False,
}  # fmt: skip
