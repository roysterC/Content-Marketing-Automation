# Painted-style infographics: free and paid tools

Research notes, October 2026. Prices change often, so check them again before building.

## The problem

Our visuals are HTML templates with line icons, rendered by Playwright
(`src/content_agent/visuals/`). They come out clean and on-brand, but they look like vector
graphics: flat shapes and thin strokes. We want a richer, painted or illustrated look that
reads as professional design work.

That look comes from **image-generation models** (diffusion or autoregressive), which output
pixels. A tool that makes code (HTML, SVG, charts) gives the same flat result we already
have, however good its layout is.

> **Gemini Canvas won't fix this.** Canvas infographics are generated **HTML code**, previewed
> in the browser, which is the same approach as our templates. It also has no API. The model
> behind Gemini's "painted" infographics is **Nano Banana Pro** (Gemini 3 Pro Image), which is
> available through the Gemini API (see the paid section).

## Two ways to use an image model

| | A. The model draws everything | B. Hybrid: the model paints, the template writes |
|---|---|---|
| What the model makes | The finished infographic, text included | Artwork only (scene, illustrated background, painted icons/objects) with **no text** |
| Where the text comes from | Drawn by the model | Our HTML template overlays crisp Inter text on top of the artwork |
| Look | Most "designed" and painterly | Painterly art with sharp, exact typography |
| Text accuracy | Good but not perfect (Nano Banana Pro gets about 85% right on the first try; long blocks and unusual terms fail) | 100%, because the text is ours |
| Risk to our rules | The model can **invent numbers or claims** that were never in the copy (conflicts with "no fabricated metrics"), and it often distorts logos | None. The existing fact-check and text-fit checks still apply |
| Consistency across an 8-slide carousel | Hard: each slide drifts in style | Easy: same template, and the art uses one style prompt or style reference |
| Models that work | Only the top text renderers (Nano Banana Pro, GPT Image 2, Seedream 5, Ideogram) | Almost any model, including free ones |

**Recommendation:**
- **Carousels: use B (hybrid).** Brand consistency and exact copy matter most over 8 slides,
  and the free tier covers it.
- **Single-image poster: try A** with Nano Banana Pro or GPT Image 2, behind a **verification
  gate**. Claude reads the rendered image and checks that every word and number matches the
  approved copy. If anything is missing, invented or misspelled, the image is regenerated, and
  after 2 tries it falls back to the HTML poster. This keeps the "no fabricated metrics" rule
  enforceable.

## Free options

| Tool | What you get | Free limit | Good for | Caveats |
|---|---|---|---|---|
| **Cloudflare Workers AI** (recommended free API) | FLUX.2 [klein] 4B/9B, FLUX.2 [dev], FLUX.1 [schnell], Leonardo **Lucid Origin** and **Phoenix 1.0** | 10,000 "neurons" per day. Rough count of 1080×1350 images per day: FLUX.1 schnell ~100+, FLUX.2 klein-9B ~6, Phoenix ~2, Lucid Origin ~1 | Option B artwork: illustrated scenes, painted backgrounds | Text rendering is weaker than the paid leaders, so keep text out of the image. Needs a free Cloudflare account plus API token. Overage is $0.011 per 1k neurons, so a few pence |
| **Pollinations.ai** | FLUX-family models via a plain URL, no key | Anonymous use: about 1 request per 15 s, **watermarked**. A free account removes the watermark | Quick experiments | No uptime guarantee, so not for the 07:00 cron |
| **Hugging Face inference credits** | FLUX schnell, SD and community models | Small monthly credit | Testing prompts | Too small for daily production |
| **Google Cloud new-account credit** | Full paid Gemini API, including Nano Banana Pro | Trial credit (~$300) ≈ 2,000 Nano Banana Pro images | A free trial of option A | Time-limited trial. After it ends this becomes the paid option |
| **Gemini app / ChatGPT / Microsoft Designer** (consumer apps) | Nano Banana Pro (about 2 free Pro images a day in the Gemini app, then it falls back to the base model), GPT Image | Small daily quotas | Roy trying styles and prompts by hand, to pick a look | **No API.** Scripting these apps breaks their terms, so they can't go in the pipeline |
| **Self-hosted open weights** (Qwen-Image, FLUX.2 klein, Z-Image) | Strong models; Qwen-Image's text rendering is close to the paid leaders | Free software | Later, if volume grows | Needs a GPU. Our small VPS can't run them, and renting a GPU isn't free. Check each model's licence |

**Can the pipeline use the free Gemini app (Canvas / Nano Banana 2)?** Not automatically.
The free Nano Banana 2 quota (about 20 images a day on a free account, per Google's help page
in March 2026) exists only inside the consumer app, which has no API. Driving the app with a
scripted, logged-in browser breaks Google's terms ("automated means") and puts Roy's whole
Google account at risk. The official Gemini CLI `nanobanana` extension also needs a Gemini API
key, so it is billed. The free route that stays within the terms is **semi-manual**: the
pipeline writes a ready-to-paste Nano Banana prompt into the Telegram review message, Roy
generates the image in the Gemini app on his phone, and he sends it back to the bot to attach
to the posting kit. The same model through the API costs $0.067 (1K) / $0.101 (2K) per image.

Note: **no Gemini image model has a free API tier.** Google's free preview path closed in
November 2025, and the pricing page lists every Nano Banana model as paid only.

## Paid options (API, can be automated)

Prices per image at about social-post resolution.

| Model | Price | Infographic strength | Notes |
|---|---|---|---|
| **Nano Banana Pro** (Gemini 3 Pro Image) | $0.134 (1K/2K), $0.24 (4K). Batch is half price | The best all-round infographic model: dense layouts, charts, accurate scale | Accepts up to 14 reference images (style guide, palette). Can ground facts with Google Search, so **disable that or verify the output** (fabrication risk) |
| **Nano Banana 2** (Gemini 3.1 Flash Image) | $0.067 (1K), $0.101 (2K). Batch is half price | Close to Pro for much less | Good default if Pro is too expensive |
| **GPT Image 2** (OpenAI, Apr 2026) | ~1024²: $0.006 low / $0.053 medium / $0.211 high. Portrait costs a bit more. Batch is half price | Highest text accuracy reported (~99% for Latin text) | Plans the image before drawing (reasoning). GPT Image 1.5 is a cheaper, slightly weaker fallback |
| **Seedream 5.0 Pro** (ByteDance, via fal.ai) | $0.0675 (≤1536²), $0.135 (≤2048²) | Very strong long-text and typography scores | Third-party host (fal) |
| **Ideogram 3.0** | $0.03 turbo / $0.06 default / $0.09 quality | Typography-first, poster style | Style reference images supported |
| **Recraft V4 Styles** | $0.04 (Pro $0.105) | Best for **brand consistency**: learns a custom style from reference images and repeats it across many generations | Use raster output. Recraft also outputs SVG, which would bring back the flat look |
| **Qwen Image 2.0** | $0.035 (Pro $0.075) | Good text and cheap | Weaker when mixing scripts (not an issue for English) |
| **FLUX.2 [pro]** (Black Forest Labs) | ~$0.03 per megapixel | Excellent painted and illustrated art | Weaker for dense text, so a good fit for option B at higher quality than the free tier |

Not suitable:
- **Midjourney:** the best aesthetics, but it has **no API** and its terms ban automation. Use
  it by hand only, for example to make style reference images.
- **Canva Connect API (autofill):** requires Canva Enterprise (30+ seats, sales-quoted).
- **Gemini Canvas, Napkin AI and other diagram tools:** they output code or vectors, which is
  the flat look we're replacing.

## What it would cost us

One package per weekday is about 22 posts a month.

| Setup | Per month |
|---|---|
| Option B carousel art on Cloudflare free tier | **£0** |
| + poster via Nano Banana 2 (2K, up to 2 tries) | ~£3–4 |
| + poster via Nano Banana Pro (up to 2 tries) | ~£4–5 |
| + poster via GPT Image 2 high quality (up to 2 tries) | ~£6–8 |
| All carousel slides fully AI-drawn with Nano Banana Pro (8 slides) | ~£20+, not recommended (consistency, text risk) |

## Suggested next step

1. Roy picks a look by hand: generate 3–4 versions of a recent poster in the Gemini app
   (Nano Banana Pro) and ChatGPT (GPT Image 2), and save the favourite as a style reference.
2. Add an `IMAGE_BACKEND` setting (`none` | `cloudflare` | `gemini` | `openai`), alongside the
   existing `LLM_BACKEND`, with a small client in `src/content_agent/visuals/`.
3. Option B first: add an artwork slot (`background-image`) to `carousel.html` and `idea.html`,
   and have the drafting prompt write a text-free art prompt per slide in one shared style.
4. Then option A for the poster, behind the Claude vision verification gate, with the HTML
   poster as the fallback.

## Sources

- Gemini API pricing (official): https://ai.google.dev/gemini-api/docs/pricing
- Nano Banana Pro launch: https://blog.google/innovation-and-ai/products/nano-banana-pro/
- Nano Banana Pro text-accuracy testing: https://www.humai.blog/i-spent-47-hours-testing-nano-banana-pros-text-rendering-for-infographics-heres-everything-i-learned-and-what-nobody-tells-you/
- Nano Banana Pro infographic review (brand and logo issues): https://venngage.com/blog/nano-banana-pro-ai-image-generator-review/
- Nano Banana Pro free limits in the Gemini app: https://erikataranto.com/en/blog/nano-banana-pro-pricing
- GCP credit for Nano Banana Pro: https://www.aifreeapi.com/en/posts/nano-banana-pro-cheap-api-alternative
- Gemini Canvas generates HTML: https://note.com/weel_media/n/n34f8b2192ec8?hl=en-US
- GPT Image 2: https://en.wikipedia.org/wiki/GPT_Image, https://wavespeed.ai/blog/posts/gpt-image-2-pricing-2026/
- GPT Image 1.5 pricing: https://pricepertoken.com/gpt-image-pricing
- Text accuracy comparison: https://ampifire.com/blog/best-ai-image-generators-with-accurate-text-in-2026-reviews-price-free-options/
- Ideogram pricing: https://developer.puter.com/tutorials/ideogram-api-pricing/
- Recraft V4 Styles: https://openrouter.ai/recraft/recraft-v4-styles, https://www.recraft.ai/docs/api-reference/pricing
- Seedream 5.0 Pro on fal: https://fal.ai/models/bytedance/seedream/v5/pro/text-to-image
- Qwen Image 2.0: https://www.therundown.ai/tools/qwen-image-2-0
- Text-rendering benchmarks (Seedream vs Qwen-Image): https://arxiv.org/html/2605.28091v1
- FLUX.2 pricing: https://docs.bfl.ml/quick_start/pricing
- Cloudflare Workers AI pricing (official): https://developers.cloudflare.com/workers-ai/platform/pricing/
- Cloudflare + Leonardo models: https://blog.cloudflare.com/workers-ai-partner-models/
- Cloudflare FLUX.2 [dev]: https://blog.cloudflare.com/flux-2-workers-ai/
- What's actually free: https://www.runflow.io/blog/free-ai-image-generation-api-lies
- Pollinations / Cloudflare free tiers: https://toolfreebie.com/cloudflare-workers-ai/
- Midjourney has no API and bans automation: https://unifically.com/blogs/midjourney-api
- Canva autofill needs Enterprise: https://layerre.com/faq/how-much-does-canva-api-cost/
