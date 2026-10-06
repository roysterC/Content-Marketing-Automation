# Painted style samples

Paste-ready Gemini (Nano Banana) prompts for the same test infographic in each art style
from `config/art_style.yaml`, so you can compare the looks before picking one. The
content is test content (illustrative numbers), not a post.

How to try one: open the Gemini app, choose image creation (🍌), paste a prompt and send.
Run each one twice to see how consistent the style is. When you've picked a style, set
`active:` in `config/art_style.yaml`, and keep your favourite image to attach as a style
reference with future prompts.

Regenerate this file after editing the styles: `python scripts/paint_samples.py`.

## Editorial gouache (`gouache`)

```text
Create a finished, professional social media infographic. Portrait, 4:5 aspect ratio
(1080 × 1350), with everything fitting inside comfortable margins.

ART STYLE (Editorial gouache)
Hand-painted editorial illustration in matte gouache, like a premium business magazine feature: visible but controlled brush strokes, soft paper grain, simple shapes with gentle painted shading, friendly rounded forms. Simple stylised people with minimal faces. Warm, calm and confident. Not cartoonish, glossy 3D, photographic or flat vector clip art.
Background: Deep navy with subtle brush texture and a soft amber glow top right. Text sits on slightly lighter navy cards with softly painted edges.
Colours: deep navy #0f1b2d, warm amber #f2a541 for highlights and key numbers, soft cream #f4f1ea, mint green #7fd1ae for good outcomes, muted slate blue #a9b4c6 for secondary text. No other strong colours.

TEXT
All text in a clean, bold, modern sans-serif (like Inter), set flat and crisp on top of the artwork: straight, sharp and easy to read on a phone, never painted, curved or hand-lettered.
Reproduce every text in “curly quotes” exactly (spelling, capitals, punctuation, numbers), once each. Add no other words, numbers, logos or watermarks anywhere, including on objects.

LAYOUT, top to bottom
1. Small amber label “AUTOMATION IDEA” beside a rounded pill “Nail salons”.
2. Headline, the largest text, in cream: “Turn missed calls into bookings”
3. Full-width painted hero illustration, about a quarter of the height: a nail technician mid-manicure while the salon phone rings unanswered on the front desk.
   No text or signs in it.
4. Slim panel with an amber left edge: “The problem:” in bold, then
   “You're mid-manicure, the phone rings, and by the time you're free the caller has booked somewhere else.”
5. Small muted label “HOW IT WORKS”, then 4 steps in a vertical
   flow joined by a painted amber line. Each has a round amber number badge with a small
   painted vignette, a bold title and one plain line (title / line):
   1. “Call goes unanswered” / “Your phone line spots the missed call, even mid-appointment.” (vignette: a phone showing a missed call)
   2. “Instant text back” / “The caller gets a friendly text with your booking link.” (vignette: a text message bubble)
   3. “They pick a slot” / “They book a free time without waiting for you.” (vignette: an open booking diary)
   4. “Reminder the day before” / “An automatic reminder cuts no-shows.” (vignette: a reminder bell)
6. A row of 3 equal cards, each a big amber number with a short label
   under it (number / label):
   - “~2 hrs” / “less time on the phone a week” (vignette: a clock)
   - “24/7” / “every caller gets a reply” (vignette: a big tick)
   - “0” / “callers left hanging” (vignette: a small group of people)
7. Small muted note under the cards: “Illustrative estimates for a typical salon”
8. Footer strip under a thin divider: “Roy · Automation for busy small businesses” on the left, “DM me "CALLS" to see it working” in amber on the right.

If I attach a reference image, match its art style, colours and finish exactly, but use
the layout and text above.
```

## Watercolour and ink (`watercolour`)

```text
Create a finished, professional social media infographic. Portrait, 4:5 aspect ratio
(1080 × 1350), with everything fitting inside comfortable margins.

ART STYLE (Watercolour and ink)
Loose watercolour washes with fine, confident ink linework, like a well-designed illustrated guide: soft colour bleeds, visible paper texture, plenty of white space. Simple stylised people with minimal faces. Light, friendly and tidy. Not cartoonish, 3D, photographic or flat vector clip art.
Background: Warm off-white watercolour paper. Text in deep navy, key numbers in amber, on pale cream cards with a thin navy ink outline.
Colours: deep navy #0f1b2d, warm amber #f2a541 for highlights and key numbers, soft cream #f4f1ea, mint green #7fd1ae for good outcomes, muted slate blue #a9b4c6 for secondary text. No other strong colours.

TEXT
All text in a clean, bold, modern sans-serif (like Inter), set flat and crisp on top of the artwork: straight, sharp and easy to read on a phone, never painted, curved or hand-lettered.
Reproduce every text in “curly quotes” exactly (spelling, capitals, punctuation, numbers), once each. Add no other words, numbers, logos or watermarks anywhere, including on objects.

LAYOUT, top to bottom
1. Small amber label “AUTOMATION IDEA” beside a rounded pill “Nail salons”.
2. Headline, the largest text, in cream: “Turn missed calls into bookings”
3. Full-width painted hero illustration, about a quarter of the height: a nail technician mid-manicure while the salon phone rings unanswered on the front desk.
   No text or signs in it.
4. Slim panel with an amber left edge: “The problem:” in bold, then
   “You're mid-manicure, the phone rings, and by the time you're free the caller has booked somewhere else.”
5. Small muted label “HOW IT WORKS”, then 4 steps in a vertical
   flow joined by a painted amber line. Each has a round amber number badge with a small
   painted vignette, a bold title and one plain line (title / line):
   1. “Call goes unanswered” / “Your phone line spots the missed call, even mid-appointment.” (vignette: a phone showing a missed call)
   2. “Instant text back” / “The caller gets a friendly text with your booking link.” (vignette: a text message bubble)
   3. “They pick a slot” / “They book a free time without waiting for you.” (vignette: an open booking diary)
   4. “Reminder the day before” / “An automatic reminder cuts no-shows.” (vignette: a reminder bell)
6. A row of 3 equal cards, each a big amber number with a short label
   under it (number / label):
   - “~2 hrs” / “less time on the phone a week” (vignette: a clock)
   - “24/7” / “every caller gets a reply” (vignette: a big tick)
   - “0” / “callers left hanging” (vignette: a small group of people)
7. Small muted note under the cards: “Illustrative estimates for a typical salon”
8. Footer strip under a thin divider: “Roy · Automation for busy small businesses” on the left, “DM me "CALLS" to see it working” in amber on the right.

If I attach a reference image, match its art style, colours and finish exactly, but use
the layout and text above.
```

## Painterly digital (`painterly`)

```text
Create a finished, professional social media infographic. Portrait, 4:5 aspect ratio
(1080 × 1350), with everything fitting inside comfortable margins.

ART STYLE (Painterly digital)
Rich painterly digital art with visible oil-like brush strokes, soft cinematic lighting and warm highlights, like a high-end editorial cover: simple, readable shapes and a clear focal point. Simple stylised people with minimal faces. Not cartoonish, plastic 3D, photographic or flat vector clip art.
Background: Deep navy with warm amber light from the top right. Text sits on dark translucent navy cards with soft edges so it stays crisp.
Colours: deep navy #0f1b2d, warm amber #f2a541 for highlights and key numbers, soft cream #f4f1ea, mint green #7fd1ae for good outcomes, muted slate blue #a9b4c6 for secondary text. No other strong colours.

TEXT
All text in a clean, bold, modern sans-serif (like Inter), set flat and crisp on top of the artwork: straight, sharp and easy to read on a phone, never painted, curved or hand-lettered.
Reproduce every text in “curly quotes” exactly (spelling, capitals, punctuation, numbers), once each. Add no other words, numbers, logos or watermarks anywhere, including on objects.

LAYOUT, top to bottom
1. Small amber label “AUTOMATION IDEA” beside a rounded pill “Nail salons”.
2. Headline, the largest text, in cream: “Turn missed calls into bookings”
3. Full-width painted hero illustration, about a quarter of the height: a nail technician mid-manicure while the salon phone rings unanswered on the front desk.
   No text or signs in it.
4. Slim panel with an amber left edge: “The problem:” in bold, then
   “You're mid-manicure, the phone rings, and by the time you're free the caller has booked somewhere else.”
5. Small muted label “HOW IT WORKS”, then 4 steps in a vertical
   flow joined by a painted amber line. Each has a round amber number badge with a small
   painted vignette, a bold title and one plain line (title / line):
   1. “Call goes unanswered” / “Your phone line spots the missed call, even mid-appointment.” (vignette: a phone showing a missed call)
   2. “Instant text back” / “The caller gets a friendly text with your booking link.” (vignette: a text message bubble)
   3. “They pick a slot” / “They book a free time without waiting for you.” (vignette: an open booking diary)
   4. “Reminder the day before” / “An automatic reminder cuts no-shows.” (vignette: a reminder bell)
6. A row of 3 equal cards, each a big amber number with a short label
   under it (number / label):
   - “~2 hrs” / “less time on the phone a week” (vignette: a clock)
   - “24/7” / “every caller gets a reply” (vignette: a big tick)
   - “0” / “callers left hanging” (vignette: a small group of people)
7. Small muted note under the cards: “Illustrative estimates for a typical salon”
8. Footer strip under a thin divider: “Roy · Automation for busy small businesses” on the left, “DM me "CALLS" to see it working” in amber on the right.

If I attach a reference image, match its art style, colours and finish exactly, but use
the layout and text above.
```
