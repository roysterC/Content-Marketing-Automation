"""Automation idea: one concrete job a business type could automate, as an infographic."""

from content_agent.formats import Format
from content_agent.visuals.render import render_idea_html
from content_agent.visuals.schemas import INFOGRAPHIC

TASK = """\
Task: come up with ONE concrete automation idea for {sector} and write it up.

What makes a good idea:
- A specific, recurring, annoying job that owners of this business type actually do by
  hand (phones, bookings, reminders, follow-ups, quotes, reviews, admin, rebooking...).
- Buildable today with ordinary tools a small business already has or can cheaply add
  (their booking system, phone line, SMS/WhatsApp, email, Google, forms).
- Easy to picture: an owner should read it and think "I do that every day".
- Different from these ideas already used (don't repeat or lightly reword them):
{recent}

Before writing, use web search to check the idea is realistic now: how this kind of
business usually takes bookings / handles the task, and that the building blocks exist.
Don't name specific software products in the post or graphic unless you've checked
they do what you say; "your booking system" is fine.

Numbers: the impact figures are illustrative estimates for a typical small business, not
claims. Keep them modest and plausible, and say so in impact_note. Only quote a real
statistic if you found it on the web, and then put its source URL in the LinkedIn
first_comment and in research_notes.

Pillar: workflow ("how {sector} could automate X").
Write the LinkedIn post, Facebook post and carousel as usual, plus the `infographic`
content for a single-image summary of the idea."""

IDEA = Format(
    name="idea",
    label="automation idea",
    task=TASK,
    visual_key="infographic",
    visual_schema=INFOGRAPHIC,
    render_visual=render_idea_html,
    title=lambda result: result["infographic"]["title"],
)
