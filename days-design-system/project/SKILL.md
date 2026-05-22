---
name: days-design
description: Use this skill to generate well-branded interfaces and assets for days, a daily diary habit supporter powered by AI Q&A. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping or production work. The system is warm beige + gold, lines & dots, gentle "appear" animations — never gamified, never marketing-y, always calm.
user-invocable: true
---

# days · design skill

Read `README.md` in this directory first — it covers product context, content fundamentals (voice, casing, microcopy with Korean + English examples), visual foundations (color, type, spacing, animation, hover/press, borders, shadows, layout, radii), and iconography. Then explore:

- `colors_and_type.css` — design tokens. Import this file at the top of any new HTML artifact (`<link rel="stylesheet" href=".../colors_and_type.css">`) and use CSS variables instead of hard-coded values.
- `assets/` — brand mark (`logo.svg`, `daisy.svg`), favicon mark (`logo-mark.svg`), and the 10 minimalist line icons in `assets/icons/` (24×24, 1.5px stroke, single color via `currentColor`).
- `ui_kits/web-app/` — high-fidelity React recreation of the days web app. Read the JSX components (`Primitives.jsx`, `Sidebar.jsx`, `ChatBubble.jsx`, `CalendarMonth.jsx`, the `screens/*.jsx`) to see exactly how the components compose, then lift the patterns into your artifact. `index.html` is the live click-through.
- `preview/*.html` — small demo cards for each token / component cluster. Use them as visual references when you need to remember "what does an AI bubble look like" or "what's the spacing scale".

## When using this skill

If creating visual artifacts (slides, mocks, throwaway prototypes, marketing pages):
- Copy needed assets out of `assets/` into your new artifact's folder — don't reference into this design system from outside.
- Always link `colors_and_type.css` (or inline the tokens you use) so the warm-paper background, ink colors, and Korean+English type pairing are correct.
- Reuse the `days-rise`, `days-pop`, `days-fade-in`, `days-slide-in`, `days-dot-pulse` keyframes for entry animations — make things appear gently, never bounce or shimmer.
- Default to the canonical card recipe: cream surface, 1px line border, 18px radius, shadow-2, 24px padding, eyebrow + serif title + hairline + body + CTA.
- Use the dot + line motifs (dot-leader rules, calendar dots, sidebar nav indicator) instead of icons whenever possible.

If working on production code for the days app itself:
- Read the source codebase (referenced from the project README's "Sources" section) for component structure, API contracts, and Korean copy.
- Reskin using these tokens — replace any indigo/gray (`#4f46e5`, `#e5e7eb`, etc) with the warm palette.
- Korean is the primary locale — keep Korean copy untouched, only replace English fallbacks if present.

If the user invokes this skill without further guidance:
- Ask what they want to build (mock screen? marketing splash? slide deck? full prototype?) and for which audience.
- Ask 3–5 quick clarifying questions before designing.
- Then act as an expert designer: produce one HTML artifact (or a small set) using this design system end-to-end, with at least one tasteful entry animation and the dot/line motif visible somewhere on screen.

## Substitution flags to be aware of

- **Fonts**: Brand serif is **Playfair Display** (variable wght 400–900 + Italic, shipped in `fonts/`). Manrope (sans), Gowun Batang / Gowun Dodum (Korean) are brand-fit picks loaded from Google Fonts — the source codebase ships no custom fonts. If real brand fonts arrive for those, drop them into `fonts/` and update the `@import` in `colors_and_type.css`.
- **Icons**: drawn from scratch in the days line style. If you need an icon not in `assets/icons/`, draw one in the same style (1.5px stroke, rounded caps, 24×24, single color), or fall back to Lucide and restroke to 1.5px.

## Never

- Use pure black (`#000`). Coffee `#2E2418` is the floor.
- Use emoji in product UI.
- Use bluish-purple gradients, neon accents, or stock photography.
- Add filler content, motivational quotes, gamification ("streak!", "great job!"), or marketing language ("unlock", "boost", "transform").
- Add background imagery beyond the optional 24px dot-grid texture.
- Use blue browser focus rings — always the gold ring (`--shadow-glow`).
