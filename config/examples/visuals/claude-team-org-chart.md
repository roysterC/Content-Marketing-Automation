# Visual reference: "Build Your Whole Team with Claude"

Image: `claude-team-org-chart.jpg` (by Adrees AI Agents, saved as a design reference,
not for reposting).

## Format
A single tall image (about 1092x1440) organised as a company org chart:
- **Headline** of 5–6 words with one accent-coloured keyword ("Team"), plus a one-line subhead
  that gives the count ("42 essential Claude skills, organised like a real company").
- **One root box** at the top ("CEO"), joined by dashed lines to **7 department columns**.
- **Each column has its own colour** (developers green, marketing red, finance teal and so on)
  and a small mascot illustration above it.
- **6 cards per column**, each with the same three lines: tool name (bold), role nickname
  (coloured, e.g. "Debt Chaser") and a 2–4 word plain description.
- **Footer** with the author handle and a follow call to action.

## Why it gets engagement
- **The framing is the hook.** "Your whole team" turns a list of tools into something an
  owner instantly understands: jobs they'd otherwise hire for.
- **The big number** (42) promises a lot of value, so people save and share it.
- **Role nicknames** ("Debt Chaser", "Hook Smith") are friendly and human, not technical.
- **Scannable.** Every card has the same structure, so readers skim it in seconds and come
  back for detail.
- **Mascots and colour** make it look like a poster, which suits LinkedIn's image feed.

## How it could map to Roy's content
- "Your salon's AI front desk team": receptionist, rebooker, review chaser, no-show
  preventer and so on, each card showing one automation and the job it replaces.
- "The 5 automations every salon should run", the lead-magnet candidate, laid out as a
  smaller grid.
- Keep Roy's rules: business problems first, plain words, no tool jargon, no invented
  numbers.

## Status
Not used automatically yet. The drafting prompt only reads `config/examples/*.md` post
text, and the infographic is a fixed template. A grid/org-chart template in
`src/content_agent/visuals/templates/` would make this format generate automatically.
