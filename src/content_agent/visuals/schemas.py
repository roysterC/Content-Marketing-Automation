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


def _obj(**props) -> dict:
    return {
        "type": "object",
        "properties": props,
        "required": list(props),
        "additionalProperties": False,
    }


def _list(items: dict, desc: str) -> dict:
    return {"type": "array", "description": desc, "items": items}


_EFFORT = {"type": "string", "enum": ["Quick win", "Afternoon", "Project"]}
_POINT = _obj(title=_str("Max ~6 words"), detail=_str("Max ~12 words"))

# A setup guide: how to build ONE automation, as an 8-page A4 PDF (templates/guide.html).
# No price fields on purpose: guides never quote prices for tools or services.
GUIDE = _obj(
    title=_str("The outcome, max ~8 words, e.g. 'Stop losing bookings to missed calls'"),
    subtitle=_str("What they'll set up and what it gets them, max ~22 words"),
    sector_label=_str("Who it's for, title case, e.g. 'Nail salons'"),
    setup_time=_str("Honest set-up time, max ~12 characters, e.g. '2-3 hours'"),
    works_with=_str("What it plugs into, max ~4 words, e.g. 'Your booking system'"),
    effort=_EFFORT,
    cost=_obj(
        headline=_str("What the problem costs them, max ~10 words"),
        body=_str("2-3 short sentences in the owner's world, max ~45 words"),
        rows=_list(
            _obj(
                label=_str("One factor of the sum, max ~8 words"),
                example=_str("Example value, max ~7 characters, e.g. '6' or '1 in 2'"),
            ),
            "3-5 factors that multiply together into the result",
        ),
        result_label=_str("What the product of the rows is, max ~8 words"),
        result_example=_str("The product of the example values, worked out correctly"),
        note=_str("Says the numbers are examples, not statistics; max ~25 words"),
        stats=_list(
            _obj(
                value=_str("Max ~7 characters"),
                label=_str("Max ~10 words"),
                source=_str("Source URL"),
            ),
            "0-2 REAL statistics found on the web, each with its source URL. Empty is fine.",
        ),
    ),
    how=_obj(
        headline=_str("The idea in one line, max ~10 words"),
        steps=_list(
            _obj(icon=ICON, title=_str("Max ~5 words"), detail=_str("Max ~12 words")),
            "3-5 steps of what happens, in order",
        ),
        business_name=_str("A made-up, clearly fictional business name for the phone mock"),
        channel=_str("Where the messages appear, e.g. 'Text message' or 'WhatsApp'"),
        event_icon=ICON,
        event=_str("What sets it off, as a phone notice, max ~4 words, e.g. 'Missed call · 10:42'"),
        conversation=_list(
            _obj(
                sender={"type": "string", "enum": ["business", "customer"]},
                text=_str("One message, max ~30 words"),
            ),
            "2-4 messages the customer sees on their phone, starting with the business",
        ),
    ),
    routes_headline=_str("Max ~6 words, e.g. 'Three ways to set it up'"),
    routes=_list(
        _obj(
            name=_str("Max ~5 words"),
            recommended={"type": "boolean", "description": "true for exactly one route"},
            best_for=_str("Completes 'Best if: ...', max ~12 words"),
            how=_str("How this route works, max ~30 words"),
            effort=_EFFORT,
            tools=_list(
                {"type": "string"},
                "1-3 tools, max ~4 words each. A product name only if checked on the web",
            ),
        ),
        "2-3 ways to set it up, simplest first",
    ),
    steps_headline=_str("Max ~6 words, e.g. 'Set it up in 6 steps'"),
    steps=_list(
        _obj(
            title=_str("An instruction, max ~7 words"),
            detail=_str("Exactly what to do, max ~30 words"),
            tip=_str("Optional tip, max ~8 words, or ''"),
        ),
        "5-7 numbered set-up steps",
    ),
    templates_headline=_str("Max ~6 words"),
    templates=_list(
        _obj(
            icon=ICON,
            when=_str("When to send it, max ~6 words"),
            message=_str(
                "Ready to send, max ~160 characters. Put the parts to swap in square "
                "brackets, e.g. [your link], [Salon name]"
            ),
        ),
        "2-3 copy-paste messages",
    ),
    checks_headline=_str("Max ~6 words"),
    mistakes=_list(_POINT, "3-4 common mistakes"),
    signals=_list(_POINT, "3-4 signs it's working, each something they can check"),
    cta=_obj(
        headline=_str("Offer to set it up for them, max ~7 words"),
        body=_str("What Roy would do for them, max ~35 words, no prices"),
    ),
)
