"""Lead funnel settings (config/funnel.yaml), shared by the guide, posts and kit.

Once the guide has a link, posts for the business types it suits end with a call to
action: LinkedIn points to the link in the first comment (links in the post body hurt
reach), Facebook asks people to comment the keyword. Roy sends the guide to commenters
by hand; the posting kit gives him the DM text.
"""

import re
from dataclasses import dataclass

import yaml

from content_agent.config import CONFIG_DIR


@dataclass(frozen=True)
class Funnel:
    guide_title: str
    guide_subtitle: str
    guide_sector: str
    guide_url: str
    keyword: str
    booking_url: str
    for_sectors: tuple[str, ...] = ()

    @property
    def live(self) -> bool:
        """Posts only promote the guide once it has a link people can open."""
        return bool(self.guide_url)

    def offers_guide(self, sector: str) -> bool:
        return self.live and sector.strip().lower() in {s.lower() for s in self.for_sectors}

    def post_instructions(self) -> str:
        """Added to the drafting prompt for posts that should promote the guide."""
        return f"""

Call to action (this post promotes Roy's free guide, "{self.guide_title}"):
- LinkedIn: end the body with one short line saying the free guide is in the first
  comment. Put this exact line first in `first_comment`: {self.linkedin_comment()}
- Facebook: end the body by asking people to comment {self.keyword} to get the free guide.
- The final carousel slide (cta) points to the guide too. Keep it low-pressure."""

    def linkedin_comment(self) -> str:
        return f"Free guide: {self.guide_title} → {self.guide_url}"

    def apply(self, result: dict) -> dict:
        """Make sure the call to action made it into the drafts, whatever Claude wrote."""
        li, fb = result["linkedin"], result["facebook"]
        comment = li.get("first_comment") or ""
        if self.guide_url not in comment:
            li["first_comment"] = "\n\n".join(filter(None, [self.linkedin_comment(), comment]))
        if "first comment" not in li["body"].lower():
            li["body"] += "\n\nFree guide in the first comment."
        if not self.asks_for_keyword(fb["body"]):
            fb["body"] += (
                f"\n\nComment {self.keyword} and I'll send you the free guide: {self.guide_title}."
            )
        return result

    def asks_for_keyword(self, text: str) -> bool:
        return bool(re.search(rf"\b{re.escape(self.keyword)}\b", text or ""))

    def promotes(self, platform: str, body: str, first_comment: str | None) -> bool:
        """Whether a saved draft carries the guide CTA (so the kit adds the DM text)."""
        if not self.live:
            return False
        if platform == "linkedin":
            return self.guide_url in (first_comment or "")
        return self.asks_for_keyword(body)

    def dm_text(self) -> str:
        """The message Roy sends to someone who commented the keyword."""
        lines = [
            f"Hi! Here's the free guide: {self.guide_title}",
            self.guide_url,
            "",
            f"Start with the first automation: it's the quickest win for most {self.guide_sector}.",
        ]
        if self.booking_url:
            lines += [
                "",
                (
                    "If you'd like to see how it would work in your business, grab a free "
                    f"20-minute chat here: {self.booking_url}"
                ),
            ]
        return "\n".join(lines)


def load_funnel(path=CONFIG_DIR / "funnel.yaml") -> Funnel:
    data = yaml.safe_load(path.read_text()) or {}
    guide = data.get("guide") or {}
    return Funnel(
        guide_title=str(guide.get("title", "")).strip(),
        guide_subtitle=str(guide.get("subtitle", "")).strip(),
        guide_sector=str(guide.get("sector", "")).strip(),
        guide_url=str(guide.get("url") or "").strip(),
        keyword=str(data.get("keyword") or "GUIDE").strip().upper(),
        booking_url=str(data.get("booking_url") or "").strip(),
        for_sectors=tuple(str(s).strip() for s in guide.get("for_sectors") or ()),
    )
