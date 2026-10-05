"""AI team: a business type's everyday jobs as automation "staff" on an org chart."""

from content_agent.formats import Format
from content_agent.visuals.render import render_orgchart_html
from content_agent.visuals.schemas import ORGCHART

TASK = """\
Task: an "AI team" org chart for {sector}: the everyday jobs this kind of business could
hand to simple automations, organised like a real staff chart.

- Pick 4 departments that match how {sector} actually run (e.g. front desk, bookings,
  marketing, admin; rename them to fit the business).
- 3 automations per department, 12 in total. Each one is a specific, recurring job owners
  do by hand today, and buildable with ordinary tools (booking system, phone, SMS or
  WhatsApp, email, forms). No futuristic or vague items ("AI strategy", "smart insights").
- Give each a friendly job-title nickname ("No-Show Guard", "Diary Filler") so it reads
  like staff, and say in 3-6 plain words what it does.
- Use web search briefly to check the jobs are realistic for {sector} today. Don't name
  specific software products.
- No numbers or claims on the chart itself.

Write the LinkedIn post, Facebook post and carousel about this "team" as usual. The
carousel can walk through the departments (e.g. a grid slide per department or two).
Pillar: workflow."""


def _title(result: dict) -> str:
    c = result["orgchart"]
    return f"{c['title_before']}{c['title_accent']}{c['title_after']}".strip()


TEAM = Format(
    name="team",
    label="AI team chart",
    task=TASK,
    visual_key="orgchart",
    visual_schema=ORGCHART,
    render_visual=render_orgchart_html,
    title=_title,
)
