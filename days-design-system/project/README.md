# days — Design System

**days** is a daily diary habit supporter. The app asks you five short questions, you answer in plain language, and an AI weaves your replies into a finished diary entry for the date. The product surface is intentionally tiny — log in, answer five, done — so the design has to feel calm, warm, and worth coming back to every evening.

This design system codifies the brand so any agent or designer can spin up new screens, decks, mocks, or marketing pages that look unmistakably like *days*.

---

## Sources

This system was built from:

- **Frontend codebase** (read-only mount): `frontend/` — React 19 + Vite + TypeScript app under `frontend/src/` (pages: Login, QnA, CalendarPage, DiaryView, Profile; Sidebar component; FullCalendar integration).
- **Public repo**: <https://github.com/55002ghals/2026-cloud-computing-days> @ `master` — full-stack source (FastAPI backend, Terraform infra, Bedrock Claude integration). The `README.md` and `Task-1.md` at the repo root describe the system architecture and product flow in Korean.

The codebase ships with a generic React-template index.css (purple `#aa3bff` accent, system-ui font) that the running app **does not actually use** — the live pages override everything with inline styles. We treated the inline-styled UI as the source of truth for layout/components but rebuilt the visual language entirely per the brief: **light beige + gold, lines + dots, gentle animation**.

> Explore those sources further if you want richer references: the GitHub repo includes screen-by-screen behavior in `Task-1.md`, and the codebase has the real API contracts under `backend/`.

---

## Product context

| | |
|---|---|
| **Name** | days |
| **One-liner** | Daily diary habit supporter, powered by AI Q&A |
| **Locale** | Korean primary (`AI 일기 QnA`), English secondary |
| **Core loop** | Pick date → AI asks Q1 → answer → Q2 → … → Q5 → diary generated → saved to calendar |
| **Surfaces** | Web app (single product). No marketing site, no mobile app yet. |
| **Auth** | Password-only ("inha-nxt" demo), single virtual user |
| **Pages** | Login, QnA chat, Calendar (monthly), Diary view (per date), Profile |

The brief is **shortest UX for daily diary habit creation**. Every screen should feel like one thing to do, calmly.

---

## Index

Files in this root:

- `README.md` — this file
- `colors_and_type.css` — design tokens (CSS variables for color, type, spacing, radius, shadow, motion)
- `SKILL.md` — agent skill manifest (`days-design`)
- `fonts/` — *(none bundled; fonts come from Google Fonts — see Type section)*
- `assets/`
  - `logo.svg`, `logo-mark.svg` — wordmark + square mark (favicon-ready)
  - `daisy.svg` — the standalone daisy mark used as a finishing dot after the wordmark
  - `icons/` — 11 line icons (pencil, eraser, calendar, user, clock, sun, arrow-right, check, close, plus, dot)
  - `legacy/` — kept-for-reference artifacts from the source repo (React-template favicon, hero.png, etc). **Not** brand assets — do not use.
- `preview/` — small HTML cards rendered in the Design System tab (one per token / component cluster)
- `ui_kits/web-app/` — high-fidelity React recreation of the days web app
  - `index.html` — interactive click-through of all five screens (login → today → 5-question chat → diary saved → calendar → diary view → profile)
  - `Logo.jsx`, `Primitives.jsx`, `Sidebar.jsx`, `ChatBubble.jsx`, `CalendarMonth.jsx`, `screens/*.jsx`, `app.jsx`
- `screenshots/` — references captured during construction (safe to ignore)

There is no slide deck for this project.

---

## CONTENT FUNDAMENTALS

The product talks to one person — the diarist — about their day. The voice is **gentle, second-person, and unhurried**. It never cheerleads, never gamifies. It treats journaling as a small private ritual.

### Voice & tone

- **Quiet, not chatty.** Sentences are short. There is no exclamation, no emoji in product copy, no "Great job!" reinforcement.
- **Second-person Korean (`-요` polite ending), or first-person reflective in diary output.** The AI addresses the user with `오늘`, `당신`, never command-form `해라`. In English fallback, use "you" / "today" / "a moment".
- **Specific over abstract.** "오늘 가장 기억에 남는 순간은 무엇이었나요?" not "Tell me about your day." Questions are concrete and small.
- **Present tense for prompts, past tense for the generated diary.** The diary reads like something the user already wrote.
- **No marketing language.** No "unlock", "boost", "transform". The product doesn't sell improvement; it makes space.

### Casing & punctuation

- **Sentence case** for buttons, labels, headings — never Title Case, never ALL CAPS except the eyebrow micro-label style.
- Korean: full-width punctuation (`，` `？`) in body copy is fine but ASCII (`,` `?`) is preferred to match the modern feel.
- Use a **middle dot `·`** as a meta separator (e.g. `2026-05-22 · 3 / 5`). Never `|`.

### Emoji & symbols

- **No emoji in product UI.** The lines-and-dots motif replaces them.
- Acceptable unicode marks (sparingly): `·` for separators, `—` for em-dash, `…` for ellipsis. That's it.

### Concrete examples (lifted or rewritten from the live app)

| Surface | Korean | English equivalent |
|---|---|---|
| App name | `AI 일기` | `days` |
| Login prompt | `비밀번호` | `Password` |
| CTA (start) | `시작` | `Begin` |
| Nav: write | `QnA 작성` | `Today's questions` |
| Nav: history | `캘린더` | `Calendar` |
| Date picker placeholder | `날짜를 선택하세요` | `Pick a date` |
| In-progress state | `Thinking...` | `Thinking…` |
| Completed | `일기 생성 완료` | `Today is saved` |
| Empty diary | `<날짜>에 일기가 없습니다.` | `No diary for this day yet.` |
| Submit hint | `Enter 전송 · Shift+Enter 줄바꿈` | `Enter to send · Shift+Enter for newline` |

### Microcopy rules of thumb

- Buttons: a single verb (`시작`, `전송`, `저장`, `확인`). Never two words if one will do.
- Errors: state what happened, then what to do. `비밀번호가 틀렸습니다.` — short, no apology theatre.
- Counters: `3 / 5` not `Question 3 of 5`. Less is more.
- Dates: ISO `YYYY-MM-DD` is the canonical machine form; in display, Korean `5월 22일` or English `May 22` is preferred for in-body copy.

---

## VISUAL FOUNDATIONS

The visual language is **warm paper + gold ink + thin rules + small dots**. Picture a leatherbound journal under a single lamp, not a SaaS dashboard.

### Color

The palette is a single warm family — there is no cool counterweight, no purple, no neon. Everything sits in the beige→gold→walnut continuum.

- **Paper** (`--paper-bone` `#FBF7EE` → `--paper-warm` `#EFE6D0`) — every background. Layered surfaces get *warmer*, not darker.
- **Ink** (`--ink-coffee` `#2E2418` → `--ink-soft` `#C2AE8E`) — text and dark accents. **Never pure black** — `#2E2418` is the floor.
- **Gold** (`--gold-deep` `#8A6A1F` → `--gold-glow` `#F4E5B6`) — the only "brand" accent. Used on the active dot, the primary button fill, the today-highlight on the calendar, and the AI bubble background.
- **Line** (`--line-faint` `#ECE2CB` → `--line-strong` `#C9B68F`) — thin rules, dotted leaders, borders.
- **Semantic** — sage `#7E8A5C` for success, clay `#B5573B` for danger, dusty sky `#6C8AA0` for info. All low-saturation, all earth-aligned.

### Type

Four families, mixed by purpose:

- **Playfair Display** (serif) — display headings, the generated diary body, and any moment that should feel "written". Variable wght 400–900 + matching Italic, shipped locally from `fonts/`.
- **Manrope** (sans) — UI: buttons, labels, nav, secondary text.
- **Gowun Batang** (Korean serif) — Korean equivalent of Playfair Display. Pairs with it inside the same line.
- **Gowun Dodum** (Korean sans) — Korean equivalent of Manrope.
- **JetBrains Mono** — counters, timestamps, the `3 / 5` chip.

> **⚠ Font substitution flag.** Brand serif is now the official **Playfair Display** (variable wght + Italic) shipped in `fonts/`. Sans (Manrope) and the Korean pairings (Gowun Batang / Gowun Dodum) are still **brand-fit substitutions** loaded from Google Fonts. If the team has chosen real brand fonts, drop the files into `fonts/` and update the `@import` line in `colors_and_type.css`.

Scale uses an arithmetic-then-jumping ladder from 11px → 72px. See `colors_and_type.css` for the full ladder and the semantic helper classes (`.t-display`, `.t-h1`, `.t-body`, `.t-body-serif`, `.t-meta`, `.t-mono`, `.t-eyebrow`).

### Spacing

Eleven-step scale, 4 → 96 px (`--s-1` to `--s-11`). The system is generous with whitespace — a card is almost always more padding than the eye expects.

### Backgrounds

- **Default page background**: solid `--paper-bone`. No image, no gradient, no noise.
- **Marketing / hero surfaces** (optional): a faint dot-grid texture using `var(--grid-dots)` at 24px pitch, 6-8% effective contrast. Lines and dots are the motif — never illustrations, never photography of food/people/desks (the genre cliché).
- **No full-bleed images.** When imagery is needed, it should be a single small line-drawn glyph (calendar squares, a sun, a dot) rendered as inline SVG using `--ink-walnut` strokes — never a stock photo.
- **No gradients on body surfaces.** A subtle warm-to-warmer gradient is acceptable only on the gold pill button (`--gold-warm` → `--gold`) and on the today-highlight dot.

### Animation

The brief is **active animation** — *not dynamic*, but everything appears. Pop, fade, slide. Every screen change should feel like the page settling onto paper.

- **Easing**: `--ease-out` (cubic-bezier(0.16, 1, 0.3, 1)) is the default. `--ease-soft` adds a tiny overshoot (1.16) for the gold button press and the calendar dot pop.
- **Durations**: `--dur-2` (240ms) for hover/fade, `--dur-3` (380ms) for slide-in and card appear, `--dur-4` (600ms) for sequenced reveals on screen entry.
- **Sequenced entry**: list items, chat bubbles, calendar days animate in with a 30–60ms stagger.
- **Keyframes**: `days-fade-in`, `days-rise`, `days-pop`, `days-slide-in`, `days-dot-pulse` — all live in `colors_and_type.css`.
- **No spinners**. The "Thinking…" state uses a row of three gold dots pulsing in sequence.
- **No bouncing icons, no parallax, no scroll-triggered nonsense.** Animation lives on entry and on interaction — that's it.

### Hover, press, focus

- **Hover (buttons)**: background shifts one step warmer (`--gold-warm` → `--gold`), no shadow change, 140ms.
- **Hover (cards / list rows)**: background fades to `--paper-mist` (almost imperceptible), border stays.
- **Hover (icons)**: opacity 0.7 → 1.0.
- **Press**: scale(0.98) + inset shadow (`--shadow-press`). No color swap; the inset does the work.
- **Focus**: 2px gold ring at 0.18 opacity (`--shadow-glow`) — never blue browser default. Always visible.
- **Disabled**: opacity 0.45, no color change, cursor `not-allowed`.

### Borders

- **Default**: `1px solid var(--line)` — soft beige `#DDCFB1`.
- **Hairline**: `1px solid var(--line-faint)` — for internal dividers inside a card.
- **Emphasized**: `1.5px solid var(--line-strong)` — for the focused input.
- **Dotted leaders**: `var(--dot-leader)` — a horizontal line of small dots, used as a section break or table-of-contents leader (e.g. `Q3 ········· 답변 완료`).
- **No double borders, no outlines** on filled buttons.

### Shadows

Three steps, all warm-tinted (rgba of `#5E461E`, not black):

- `--shadow-1` — barely-there lift for input fields on focus.
- `--shadow-2` — default card shadow.
- `--shadow-3` — modal / dropdown / chat composer raised over content.
- `--shadow-glow` — the focus ring.
- `--shadow-press` — inset for pressed state.

No inner-shadow effects on regular surfaces. No coloured glows other than gold.

### Transparency & blur

- **Sticky composer at the bottom of the QnA screen** uses `background: rgba(251, 247, 238, 0.92)` + `backdrop-filter: blur(8px)` so chat content peeks through as you scroll. This is the **only** place blur is used.
- Modals use a solid `--paper-cream` panel over a `rgba(46, 36, 24, 0.32)` scrim — no blur on the scrim.

### Layout rules

- **One column, centered.** Max content width 640px for chat/diary, 860px for calendar, 400px for login. The sidebar is 220px wide on desktop, collapses to a top bar on narrow viewports.
- **Sidebar is fixed**, content scrolls. The composer at the bottom of QnA is sticky.
- **Grid baseline**: 8px. Everything snaps. The dot-grid texture uses 24px (3× baseline).
- **No "split-screen" hero layouts**, no side-by-side feature columns. The app is a diary; it reads top to bottom.

### Corner radii

- Buttons: `--r-pill` (999px) for primary CTAs, `--r-3` (12px) for secondary text buttons.
- Inputs / textareas: `--r-3` (12px).
- Cards / chat bubbles: `--r-4` (18px), with one corner squared on chat bubbles to indicate speaker (`0 18px 18px 18px` for AI, `18px 0 18px 18px` for user).
- Modals: `--r-5` (24px).
- Avatar / dot: `--r-pill`.

### Card anatomy

A card on *days* is:

- Background `--paper-cream`
- 1px `--line` border
- `--r-4` radius
- `--shadow-2`
- Inner padding `--s-6` (24px)
- Optional eyebrow label at top (`.t-eyebrow`, gold, all-caps, letterspaced)
- Optional thin `--line-faint` divider between sections
- Title in serif (`.t-h2` or `.t-h3`)
- Body in sans (`.t-body`) or serif (`.t-body-serif`) for diary content

No coloured left-border accent. No drop-cap. No gradient bg.

### Iconography vibe (preview — full section below)

Line-only. 1.5px stroke. Rounded caps. 24×24 base. Walnut color on paper. Gold only when the icon is the selected state of a tab.

---

## ICONOGRAPHY

The brand uses **outline-only line icons** in 1.5px stroke, with rounded caps and joins, on a 24×24 grid. The walnut ink color (`--ink-walnut`) is the default fill stroke; gold (`--gold`) is reserved for the selected/active state of a navigation item or the indicator dot.

### What ships in this system

- **Logo mark** — `assets/logo.svg` — wordmark "days" set in Playfair Display Italic with a tiny gold-petal daisy used as a finishing dot (like a period after the word).
- **Daisy** — `assets/daisy.svg` — standalone 24×24 daisy: six filled teardrop petals in `--gold-warm` around a `--paper-bone` circle. Used as the brand mark wherever the wordmark isn't appropriate (favicon background, loading splash, small accents).
- **Icon set** — `assets/icons/` — 11 line icons covering the entire current product surface: `pencil` (write), `eraser` (edit / clear), `calendar`, `user`, `clock`, `sunrise` (sun with 4 rays), `arrow-right`, `check`, `close`, `plus` (sparkle/add), `dot` (the bullet / pulse / today marker). All 24×24 viewBox, 1.5px stroke, single path where possible, `currentColor` so they inherit the parent's color.
- **Three-dot thinking indicator** — implemented as a small JSX component in the UI kit (`ThinkingDots.jsx`), not an asset, because it animates.

### Approach

- **No emoji.** Anywhere.
- **No unicode-as-icon** (no `★`, no `→`, no `✓`). We use SVG so stroke and color are controllable.
- **No icon font.** Loading a webfont just for icons is heavy and inflexible; SVG sprites are better for a set this small.
- **No multi-color icons.** Every icon is one color. The selected state changes the color, never the shape.
- **No filled icons.** Outline only. The single exception is the today-dot, which is a filled disk because that's the dot motif's literal expression.
- **No icon-only buttons in the main flow** — every navigation item has its label visible (e.g. the sidebar shows the pencil icon *and* "QnA 작성"). Icon-only is reserved for tertiary actions like closing a modal.

### When the codebase had something we couldn't use

The source repo ships `frontend/public/icons.svg` — a sprite of social/docs icons (GitHub, X, Bluesky, Discord) from the React Vite template. **These are not brand icons.** They're in `assets/legacy/template-icons.svg` for reference only. Don't use them; if you need a social icon for marketing, draw a new one in the days line-only style.

If a new icon is needed and isn't in `assets/icons/`, the substitution rule is:
1. **Prefer** drawing one to match the existing set (1.5px stroke, rounded caps, 24×24, single color).
2. **Fallback** to [Lucide](https://lucide.dev) — same stroke style, same grid. If you pull one in, restroke to 1.5px and recolor to `currentColor`.
3. **Flag the substitution** in the README of whatever artifact uses it.

---

*See `SKILL.md` for the agent-invocable summary of this system.*
