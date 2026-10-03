"""Text-fit check and the org-chart template, with rendering and Claude faked out."""

from pathlib import Path

from content_agent.drafting import fit


def test_fit_problems_flags_only_cramped_visuals():
    problems = fit.fit_problems([1.0, 0.9, 0.8], ["slide 1", "slide 2", "slide 3"])
    assert problems == ["slide 3: text had to shrink to 80% to fit"]


def test_carousel_is_shortened_and_rerendered_when_cramped(monkeypatch):
    renders = []

    def fake_render(slides, out_stem):
        renders.append(slides)
        return Path("x.pdf"), [1.0, 0.75] if len(renders) == 1 else [1.0, 0.95]

    seen = {}

    def fake_tighten(data, schema, problems):
        seen["problems"] = problems
        return {"slides": [{"title": "short"}, {"title": "shorter"}]}

    monkeypatch.setattr(fit, "render_carousel", fake_render)
    monkeypatch.setattr(fit, "tighten", fake_tighten)

    _, slides = fit.render_carousel_fitted([{"layout": "cover"}, {"layout": "steps"}], Path("x"))

    assert len(renders) == 2
    assert seen["problems"] == ["slide 2 (steps): text had to shrink to 75% to fit"]
    assert slides == [{"title": "short"}, {"title": "shorter"}]


def test_carousel_that_fits_costs_no_extra_call(monkeypatch):
    monkeypatch.setattr(fit, "render_carousel", lambda s, o: (Path("x.pdf"), [1.0]))
    monkeypatch.setattr(fit, "tighten", lambda *a: (_ for _ in ()).throw(AssertionError))
    _, slides = fit.render_carousel_fitted([{"layout": "cover"}], Path("x"))
    assert slides == [{"layout": "cover"}]


def test_orgchart_renders_departments_and_cards():
    from content_agent.visuals.render import render_orgchart_html

    role = {"icon": "phone", "name": "Reminders", "nickname": "No-Show Guard", "does": "<b>x</b>"}
    chart = {
        "title_before": "Your Salon's ", "title_accent": "AI Team", "title_after": "",
        "subtitle": "12 automations", "root_label": "The owner", "root_name": "Your salon",
        "root_icon": "user", "cta": "DM me TEAM",
        "departments": [{"name": f"Dept {n}", "icon": "calendar", "roles": [role] * 3}
                        for n in range(4)],
    }  # fmt: skip
    html = render_orgchart_html(chart)
    assert html.count('class="card"') == 12
    assert html.count('class="dept"') == 4
    assert "<em>AI Team</em>" in html
    assert "<b>x</b>" not in html
