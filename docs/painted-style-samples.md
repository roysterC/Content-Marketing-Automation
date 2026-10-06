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
Design a professional, eye-catching social media infographic for small-business owners
on LinkedIn and Facebook. Portrait, 4:5 aspect ratio (1080 × 1350). Show how one everyday job gets automated: the problem, how the fix works step by step, and what it changes.

YOUR CREATIVE FREEDOM
You choose the layout, composition, hierarchy and how to show the information: a flow,
path, timeline, scene with callouts, cards, before and after, or anything else that tells
it clearly. Make it distinctive, not a template. It must read easily on a phone: a clear
focal point, standout headline and numbers, steps in order, comfortable margins, and the
signature small at the bottom.

FIXED DESIGN SYSTEM (identical on every post, follow it exactly)
Art style (Editorial gouache): Hand-painted editorial illustration in matte gouache, like a premium business magazine feature: visible but controlled brush strokes, soft paper grain, simple shapes with gentle painted shading, friendly rounded forms. Simple stylised people with minimal faces. Warm, calm and confident. Not cartoonish, glossy 3D, photographic or flat vector clip art.
Background: Deep navy with subtle brush texture and soft warm amber light.
Font: One geometric sans-serif (like Inter) for all text: extra-bold headline, semibold labels and numbers, regular body. Flat and crisp on top of the artwork, never painted, curved or hand-lettered.
Colours: Deep navy #0f1b2d, cream #f4f1ea for main text, warm amber #f2a541 for highlights, key numbers and the call to action, mint #7fd1ae for good outcomes, slate blue #a9b4c6 for secondary text. No other strong colours.
Lines: One weight for every line, arrow and divider, about 3 px, rounded ends; amber where it shows flow.
Boxes: Rounded corners (about 24 px), filled slightly lighter than the background, no border or a thin 2 px tint, no hard shadows.
Icons: Small, same-size icons painted in the illustration's technique, mostly amber and cream; never emoji or thin vector line icons.

CONTENT
Use every “curly-quoted” text word for word, once each; text marked optional may be left out. Add no other words, numbers, logos or watermarks, including on objects.
- Label: “Automation idea”
- Business type: “Nail salons”
- Headline: “Turn missed calls into bookings”
- The problem: “You're mid-manicure, the phone rings, and by the time you're free the caller has booked somewhere else.”
- How it works, 4 steps in this order (title / one line):
  1. “Call goes unanswered” / “Your phone line spots the missed call, even mid-appointment.”
  2. “Instant text back” / “The caller gets a friendly text with your booking link.”
  3. “They pick a slot” / “They book a free time without waiting for you.”
  4. “Reminder the day before” / “An automatic reminder cuts no-shows.”
- Results, 3 figures (number / label):
  - “~2 hrs” / “less time on the phone a week”
  - “24/7” / “every caller gets a reply”
  - “0” / “callers left hanging”
- Note on the figures, small: “Illustrative estimates for a typical salon”
- Call to action: “DM me "CALLS" to see it working”
- Signature, small: “Roy · Automation for busy small businesses”
- Optional section headings: “The problem”, “How it works”, “The result”
- Illustration idea (optional, adapt or replace): a nail technician mid-manicure while the salon phone rings unanswered on the front desk

If I attach a reference image, match its art style, font, colours, line weight and box
style exactly, but design your own layout for this content.
```

## Watercolour and ink (`watercolour`)

```text
Design a professional, eye-catching social media infographic for small-business owners
on LinkedIn and Facebook. Portrait, 4:5 aspect ratio (1080 × 1350). Show how one everyday job gets automated: the problem, how the fix works step by step, and what it changes.

YOUR CREATIVE FREEDOM
You choose the layout, composition, hierarchy and how to show the information: a flow,
path, timeline, scene with callouts, cards, before and after, or anything else that tells
it clearly. Make it distinctive, not a template. It must read easily on a phone: a clear
focal point, standout headline and numbers, steps in order, comfortable margins, and the
signature small at the bottom.

FIXED DESIGN SYSTEM (identical on every post, follow it exactly)
Art style (Watercolour and ink): Loose watercolour washes with fine, confident ink linework, like a well-designed illustrated guide: soft colour bleeds, visible paper texture, plenty of white space. Simple stylised people with minimal faces. Light, friendly and tidy. Not cartoonish, 3D, photographic or flat vector clip art.
Background: Warm off-white watercolour paper.
Font: One geometric sans-serif (like Inter) for all text: extra-bold headline, semibold labels and numbers, regular body. Flat and crisp on top of the artwork, never painted, curved or hand-lettered.
Colours: Deep navy #0f1b2d for main text and ink lines, warm amber #f2a541 for highlights, key numbers and the call to action, mint #7fd1ae for good outcomes, slate blue #a9b4c6 for secondary text. No other strong colours.
Lines: One weight for every line, arrow and divider, about 3 px, rounded ends; amber where it shows flow.
Boxes: Rounded corners (about 24 px), a pale cream wash inside and a thin navy ink outline, no shadows.
Icons: Small, same-size icons painted in the illustration's technique, mostly amber and cream; never emoji or thin vector line icons.

CONTENT
Use every “curly-quoted” text word for word, once each; text marked optional may be left out. Add no other words, numbers, logos or watermarks, including on objects.
- Label: “Automation idea”
- Business type: “Nail salons”
- Headline: “Turn missed calls into bookings”
- The problem: “You're mid-manicure, the phone rings, and by the time you're free the caller has booked somewhere else.”
- How it works, 4 steps in this order (title / one line):
  1. “Call goes unanswered” / “Your phone line spots the missed call, even mid-appointment.”
  2. “Instant text back” / “The caller gets a friendly text with your booking link.”
  3. “They pick a slot” / “They book a free time without waiting for you.”
  4. “Reminder the day before” / “An automatic reminder cuts no-shows.”
- Results, 3 figures (number / label):
  - “~2 hrs” / “less time on the phone a week”
  - “24/7” / “every caller gets a reply”
  - “0” / “callers left hanging”
- Note on the figures, small: “Illustrative estimates for a typical salon”
- Call to action: “DM me "CALLS" to see it working”
- Signature, small: “Roy · Automation for busy small businesses”
- Optional section headings: “The problem”, “How it works”, “The result”
- Illustration idea (optional, adapt or replace): a nail technician mid-manicure while the salon phone rings unanswered on the front desk

If I attach a reference image, match its art style, font, colours, line weight and box
style exactly, but design your own layout for this content.
```

## Painterly digital (`painterly`)

```text
Design a professional, eye-catching social media infographic for small-business owners
on LinkedIn and Facebook. Portrait, 4:5 aspect ratio (1080 × 1350). Show how one everyday job gets automated: the problem, how the fix works step by step, and what it changes.

YOUR CREATIVE FREEDOM
You choose the layout, composition, hierarchy and how to show the information: a flow,
path, timeline, scene with callouts, cards, before and after, or anything else that tells
it clearly. Make it distinctive, not a template. It must read easily on a phone: a clear
focal point, standout headline and numbers, steps in order, comfortable margins, and the
signature small at the bottom.

FIXED DESIGN SYSTEM (identical on every post, follow it exactly)
Art style (Painterly digital): Rich painterly digital art with visible oil-like brush strokes, soft cinematic lighting and warm highlights, like a high-end editorial cover: simple, readable shapes and a clear focal point. Simple stylised people with minimal faces. Not cartoonish, plastic 3D, photographic or flat vector clip art.
Background: Deep navy with warm amber light falling across it.
Font: One geometric sans-serif (like Inter) for all text: extra-bold headline, semibold labels and numbers, regular body. Flat and crisp on top of the artwork, never painted, curved or hand-lettered.
Colours: Deep navy #0f1b2d, cream #f4f1ea for main text, warm amber #f2a541 for highlights, key numbers and the call to action, mint #7fd1ae for good outcomes, slate blue #a9b4c6 for secondary text. No other strong colours.
Lines: One weight for every line, arrow and divider, about 3 px, rounded ends; amber where it shows flow.
Boxes: Rounded corners (about 24 px), dark translucent navy with soft edges so text stays crisp over the painting, no border, no hard shadows.
Icons: Small, same-size icons painted in the illustration's technique, mostly amber and cream; never emoji or thin vector line icons.

CONTENT
Use every “curly-quoted” text word for word, once each; text marked optional may be left out. Add no other words, numbers, logos or watermarks, including on objects.
- Label: “Automation idea”
- Business type: “Nail salons”
- Headline: “Turn missed calls into bookings”
- The problem: “You're mid-manicure, the phone rings, and by the time you're free the caller has booked somewhere else.”
- How it works, 4 steps in this order (title / one line):
  1. “Call goes unanswered” / “Your phone line spots the missed call, even mid-appointment.”
  2. “Instant text back” / “The caller gets a friendly text with your booking link.”
  3. “They pick a slot” / “They book a free time without waiting for you.”
  4. “Reminder the day before” / “An automatic reminder cuts no-shows.”
- Results, 3 figures (number / label):
  - “~2 hrs” / “less time on the phone a week”
  - “24/7” / “every caller gets a reply”
  - “0” / “callers left hanging”
- Note on the figures, small: “Illustrative estimates for a typical salon”
- Call to action: “DM me "CALLS" to see it working”
- Signature, small: “Roy · Automation for busy small businesses”
- Optional section headings: “The problem”, “How it works”, “The result”
- Illustration idea (optional, adapt or replace): a nail technician mid-manicure while the salon phone rings unanswered on the front desk

If I attach a reference image, match its art style, font, colours, line weight and box
style exactly, but design your own layout for this content.
```
