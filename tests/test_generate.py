"""Morning generator: settings, random picks and the daily loop (Claude/rendering faked)."""

import random

import pytest

from content_agent import generate
from content_agent.formats import FORMATS


def _settings(**kw):
    base = {
        "posts_per_day": 1,
        "format_weights": {"idea": 75, "team": 25},
        "sector_weights": {"nail salons": 2, "barbers": 1, "dog groomers": 1},
        "avoid_recent_sectors": 2,
    }
    return generate.Settings(**{**base, **kw})


def test_shipped_settings_load_and_match_registered_formats():
    s = generate.load_settings()
    assert s.posts_per_day == 1
    assert s.format_weights == {"idea": 67, "team": 23, "offer": 10}
    assert set(s.format_weights) <= set(FORMATS)
    assert s.sector_weights["nail salons"] > s.sector_weights["barbers"]


def test_unknown_format_in_settings_is_rejected(tmp_path):
    bad = tmp_path / "formats.yaml"
    bad.write_text("formats: {idea: 1, podcast: 1}\nsectors: {barbers: 1}\n")
    with pytest.raises(ValueError, match="podcast"):
        generate.load_settings(bad)


def test_format_pick_follows_weights_roughly():
    rng = random.Random(1)
    picks = [generate.pick_format(_settings(), rng).name for _ in range(4000)]
    share = picks.count("idea") / len(picks)
    assert 0.72 < share < 0.78


def test_sector_pick_skips_recently_used_business_types():
    rng = random.Random(2)
    recent = ["nail salons", "barbers", "dog groomers"]  # only first 2 are avoided
    picks = {generate.pick_sector(_settings(), recent, rng) for _ in range(200)}
    assert picks == {"dog groomers"}


def test_sector_pick_allows_repeats_when_everything_is_recent():
    s = _settings(sector_weights={"barbers": 1}, avoid_recent_sectors=3)
    assert generate.pick_sector(s, ["barbers"]) == "barbers"


def test_daily_makes_posts_per_day_packages(monkeypatch):
    calls = []
    monkeypatch.setattr(generate, "load_settings", lambda: _settings(posts_per_day=2))
    monkeypatch.setattr(
        generate, "generate", lambda name, sector=None: calls.append(name) or [1, 2]
    )
    assert generate.daily() == [1, 2, 1, 2]
    assert len(calls) == 2 and set(calls) <= set(FORMATS)


def test_every_format_task_takes_sector_and_recent():
    for fmt in FORMATS.values():
        prompt = fmt.task.format(sector="barbers", recent="  - x", guide_outline="", keyword="G")
        assert "barbers" in prompt


def test_offer_sits_out_until_the_guide_is_live():
    s = _settings(format_weights={"idea": 67, "team": 23, "offer": 10})
    rng = random.Random(3)
    assert "offer" not in {generate.pick_format(s, rng).name for _ in range(500)}
    picks = [generate.pick_format(s, rng, guide_live=True).name for _ in range(4000)]
    assert 0.07 < picks.count("offer") / len(picks) < 0.13
    assert 0.72 < picks.count("idea") / (picks.count("idea") + picks.count("team")) < 0.78
