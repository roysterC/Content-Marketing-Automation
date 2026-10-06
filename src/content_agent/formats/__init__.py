"""Content formats: the kinds of post the morning generator can make.

Each format is one small definition: the task Claude is given, the single-image visual
it fills, and how to title it. Everything else (picking a business type, research,
fact-check, saving, rendering, the text-fit check, Telegram) is shared, in
content_agent.generate. Adding a format = adding a module here and an entry in FORMATS;
it then gets a weight in config/formats.yaml and a /<name> Telegram command for free.
"""

from collections.abc import Callable
from dataclasses import dataclass

from content_agent.drafting.draft import post_schema


@dataclass(frozen=True)
class Format:
    name: str  # CLI/Telegram name, also stored as the Item category, e.g. "idea"
    label: str  # how it's described to Roy, e.g. "automation idea"
    task: str  # prompt; may use {sector}, {recent}, {guide_outline} and {keyword}
    visual_key: str  # key of the single-image visual in Claude's JSON
    visual_schema: dict
    render_visual: Callable[[dict], str]  # visual JSON -> HTML
    title: Callable[[dict], str]  # Claude's JSON -> short title stored for history
    pillar: str = "workflow"
    # Only makes sense once the free guide is live (config/funnel.yaml), and only for the
    # business types it suits. Skipped by the daily pick until then.
    promotes_guide: bool = False

    @property
    def schema(self) -> dict:
        return post_schema(self.visual_key, self.visual_schema, research_notes=True)


def _registry() -> dict[str, Format]:
    from content_agent.formats.idea import IDEA
    from content_agent.formats.offer import OFFER
    from content_agent.formats.team import TEAM

    return {f.name: f for f in (IDEA, TEAM, OFFER)}


FORMATS: dict[str, Format] = _registry()
