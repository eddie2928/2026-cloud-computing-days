# Days — Design System

**Days** is a Korean AI diary app — *"Your AI Diary."* The app asks you five gentle questions each evening, you answer in plain language, and an AI weaves your replies into a finished diary entry tagged with the day's mood. The whole product surface is intentionally small: log in → pick a date → answer five → done.

This design system codifies the brand so any agent or designer can spin up new screens, mocks, slides, or marketing pages that feel unmistakably like *Days* — **soft sage green, warm cream paper, floating cloud + leaf shapes, real emoji for mood, and Korean-first copy**.

---

## Sources

This system was built from:

- **Brand reference screenshots** — six mocks of the app shipped by the team: login, onboarding (profile setup), monthly mood calendar, diary detail modal (emoji + body), AI 5-question chat session, profile edit. These are the *visual* source of truth; copy hex values from `colors_and_type.css` come from sampling the actual pixels in these screenshots.
- **Public GitHub repo** — <https://github.com/55002ghals/2026-cloud-computing-days> @ `master`. Full-stack source (FastAPI + Bedrock Claude backend, React 19 + Vite frontend, Terraform infra). The repo describes the **product flow & data model** (5-question AI Q&A loop, emotion enum `happy / sad / angry / neutral / bored`, profile fields, calendar contract). The frontend's *visual* language in the repo is a different ("warm beige + gold") direction that has since been **superseded** by the green/cloud screenshots — only the structure was carried over.
- **Korean product copy** in this system is lifted verbatim from the screenshots and from the repo's pages (`Login.tsx`, `Onboarding.tsx`, `QnA.tsx`, `Profile.tsx`).

Anyone reading this system who wants more depth — API contracts, screen behavior, the AI prompt template — should explore that GitHub repo. The Tasks document at the repo root walks through screen-by-screen behavior in Korean.

> **For the next agent**: the upstream repo is the place to look up *what* a screen does. This design system tells you *how* it should look.

---

## Product context

| | |
|---|---|
| **Name** | Days |
| **Tagline** | Your AI Diary. |
| **One-liner** | AI asks five short questions, you reply, it writes your diary. |
| **Locale** | Korean primary, English fallback for global pitch decks |
| **Surfaces** | Mobile web app (responsive). No native app yet, no marketing site. |
| **Auth** | Email + password, or "Continue with Google" |
| **Screens** | Login → Onboarding → Calendar (home) → Chat (Q&A modal) → Diary detail (modal) → Profile edit |
| **Core loop** | Open app → tap an empty calendar day → AI Q1 → you answer → … → Q5 → diary saved with mood emoji → back to calendar |
| **Mood model** | 5 emotions: 😊 happy · 😭 sad · 😠 angry · 😐 neutral · 😩 bored |

The brief is **shortest UX for daily diary habit creation**. Every screen should feel like one quiet thing to do.

---

## Index

Files in this root:

- `README.md` — this file
- `colors_and_type.css` — design tokens (colors, type, spacing, radius, shadow, motion + keyframes + base typography classes). Import this at the top of every new artifact.
- **`themes.css`** — four **seasonal palettes** layered on top of the base tokens. Apply with a single `data-season` attribute and the entire UI re-themes. See *Seasonal themes* below.
- `SKILL.md` — agent skill manifest (`days-design`), for cross-compat with Claude Code skills.
- `fonts/` — *empty.* Fonts come from Google Fonts (see `colors_and_type.css`). See the Type section in Visual Foundations for the substitution flag.
- `assets/`
  - `logo-cloud.svg` — the brand mark: a cloud outline with a leaf-shaped P inside. Use this on hero / login / loading.
  - `logo-mark.svg` — solid version, suitable as a favicon / OG image badge.
  - `leaf.svg` — standalone leaf shape, used as a small decorative accent.
  - `cloud-bg.svg` — soft white cloud silhouette for backgrounds.
  - `icons/` — 20 line icons (1.75px stroke, 24×24, single-color via `currentColor`).
- `preview/` — small HTML cards rendered in the Design System tab (colors, type, components).
- `ui_kits/web-app/` — high-fidelity React recreation of the Days app
  - `index.html` — interactive click-through of all six screens.
  - `app.jsx`, `Logo.jsx`, `Primitives.jsx`, `screens/*.jsx` — JSX components.

There is no slide deck for this project. If you need to make pitch slides, lean on `colors_and_type.css` and lift visual language from the login screen.

---

## SEASONAL THEMES

Days re-skins itself by season. The visual *system* (type, layout, motion, components) stays identical — only the color palette swaps. Drop `themes.css` next to `colors_and_type.css`, and apply one attribute:

```html
<link rel="stylesheet" href="colors_and_type.css">
<link rel="stylesheet" href="themes.css">
<body data-season="summer">   <!-- spring | summer | autumn | winter -->
```

| Season | Months | Primary | Vibe |
|---|---|---|---|
| **봄 Spring** | 3 – 5월 | `#7D9D6A` sage leaf | Cloud + leaf (default) |
| **여름 Summer** | 6 – 8월 | `#4FA3D6` sky | Clear, breezy, bright |
| **가을 Autumn** | 9 – 11월 | `#D88444` warm orange | Fallen leaves, late afternoon |
| **겨울 Winter** | 12 – 2월 | `#8194AB` cool slate | Snow, frost, hushed |

Everything rebinds: page gradient, CTA fill, hover state, focus ring, chat user-bubble, calendar today-ring, decorative blobs, avatar, even shadows tinted to match. Spring is the default (no attribute needed). The UI kit at `ui_kits/web-app/index.html` has a season toggle at the top — switch it to see the same six screens in all four palettes.

To **auto-pick** based on the current month, drop this snippet in `<head>`:

```html
<script>
  const m = new Date().getMonth() + 1;
  document.documentElement.dataset.season =
    m <= 2 || m === 12 ? 'winter' : m <= 5 ? 'spring' : m <= 8 ? 'summer' : 'autumn';
</script>
```

---

## CONTENT FUNDAMENTALS

Days talks to one person — the diarist — about their day. The voice is **gentle, polite (`-요` ending), and brief**. It treats journaling as a private ritual, never a productivity game.

### Voice & tone

- **Calm, never cheerful.** No "Great job!", no streaks, no badges. The product helps you write; it doesn't congratulate you for writing.
- **Korean polite informal (`-요` ending).** `오늘 하루는 어떠셨나요?` not `오늘 하루는 어떠셨습니까?` (too formal) and not `오늘 어때?` (too casual). The voice is a thoughtful friend.
- **Second person for prompts, first person reflective for the generated diary.** AI asks → user answers → AI writes the entry back as if the user wrote it.
- **Specific questions.** `기억에 남는 순간이 있었나요?` — concrete. Never `Tell me about your day`.
- **Short.** Buttons are one word (`저장`, `시작`, `다음`, `전송`). Errors state what happened in <10 words.

### Casing & punctuation

- **Korean primary** with optional English secondary. Korean copy keeps its native punctuation (`,` `?` `.`).
- **Sentence case** for labels and buttons. Never Title Case, never ALL CAPS.
- Use `오후 9:00` for times (not `21:00`), `2026년 5월` for months, `5월 22일 (목)` for dates with weekday.
- Middle dot `·` is the meta separator (e.g. `행복 · 탭하여 수정`). Never `|`.

### Emoji & symbols

- **Real emoji are used — but ONLY for moods.** The five mood faces (😊 😭 😠 😐 😩) are the product's defining visual element and replace any line-icon representation of mood. They appear in the calendar, the diary detail header, and the AI chat as user reactions.
- **No decorative emoji.** No ✨ in headings, no 🎉 on the success screen, no 👀 in chat.
- **Required field marker** is `*` in `--accent-clay` (a warm clay-red), placed after the label: `닉네임 *`.

### Concrete copy examples (lifted from screens)

| Surface | Korean (verbatim) | English |
|---|---|---|
| App name | `Days` | Days |
| Tagline | `Your AI Diary` | Your AI Diary. |
| Login CTA | `Log In` | Log In |
| Login secondary | `Continue with Google` | Continue with Google |
| Forgot link | `Forgot password?` | Forgot password? |
| Separator | `or` | or |
| Onboarding title | `프로필을 알려주세요` | Tell us about you |
| Onboarding hint | `맞춤형 질문을 위해 사용돼요` | Used to tailor your questions |
| Profile fields | `닉네임 *`, `성별 *`, `나이 *`, `관심사` | Nickname, Gender, Age, Interests |
| Calendar header | `2026년 5월` | May 2026 |
| Diary header | `5월 22일 (목)` | Thu, May 22 |
| Mood prompt | `행복 · 탭하여 수정` | Happy · tap to edit |
| Chat header | `오늘의 기록 가이드` | Today's reflection |
| Chat Q1 | `오늘 하루는 어떠셨나요?` | How was your day? |
| Chat Q2 | `기억에 남는 순간이 있었나요?` | A moment that stayed with you? |
| Composer placeholder | `답변을 입력하세요` | Type your answer |
| Progress | `2 / 5` | 2 / 5 |
| Profile save | `저장` | Save |
| Logout | `로그아웃` | Log out |

### Microcopy rules of thumb

- Counters: `2 / 5` not `Question 2 of 5`. Less is more.
- Errors: `비밀번호가 틀렸습니다.` — no apology theatre, no `Sorry, but…`.
- Empty states: `아직 작성된 일기가 없어요.` — soft, never a wall.
- Loading: a 3-dot pulse on the AI bubble. No spinners with text.

---

## VISUAL FOUNDATIONS

The visual language is **soft sage paper + cloud + leaf**. Picture sitting in a garden in late afternoon — diffused light, a single leaf drifting past — not a SaaS dashboard.

### Color

A single warm-natural family — cream paper above, sage green below, no cool counterweight, no neon. Everything sits in the cream → sage → forest continuum.

- **Paper / cream** (`--paper-bone` `#FCF6EC` → `--paper-warm` `#FBF3E8` → `--paper-pure` `#FFFFFF`) — page top, card surface, input field, AI bubble.
- **Sage** (`--sage-leaf` `#7D9D6A` is the PRIMARY GREEN — every CTA, the user chat bubble, the today-ring on the calendar, progress fill, active chip. `--sage-forest` `#475A33` for logo + headings, `--sage-ink` `#2E3B1F` for primary text. `--sage-fern` `#A2BA8D` for hover. `--sage-wash` `#E3F2E4` for the lower half of every screen.)
- **Ink** (`--ink-deep` `#1F2818` → `--ink-hint` `#9BA590`) — body and meta text. Never pure black.
- **Lines** (`--line` `#DDDED0`) — input rest border, inactive chip border, hairline dividers.
- **Semantic** — `--accent-clay` `#B5573B` for required-asterisk + logout + danger. `--accent-honey` `#D9A441` for warning. `--accent-sky` `#6C8AA0` for info. All low-saturation, all earth-aligned.

There is **no purple, no blue-indigo, no neon**. The codebase ships with a leftover `#4f46e5` indigo from a Vite template — **never use it**.

### Type

- **Pretendard** (variable Korean+Latin sans) — the entire UI. The *"Days"* wordmark is Pretendard 800 with very tight tracking (`-0.04em`). UI body, labels, buttons, Korean copy — all the same family at different weights (400/500/600/800).
- **Inter** — latin-only fallback; metrics match Pretendard so chains gracefully if Pretendard fails to load.
- **Noto Sans KR** — ultimate Korean fallback.
- **Noto Serif KR** — the only place serif appears: optional emphasis on a long diary-body paragraph. The screenshots actually keep diary body in sans, so use serif only when the artifact specifically calls for an "old journal" tone.
- **JetBrains Mono** — counters (`2 / 5`), dates in machine form (`2026-05-22`), timestamps.

> **⚠ Font substitution flag.** Pretendard is the most-likely real choice for a Korean product of this aesthetic (it's the de-facto open-source Korean sans), but the actual brand font could also be Wanted Sans, SUITE, or Apple SD Gothic Neo. Pretendard is loaded from a CDN in `colors_and_type.css`. If real brand fonts arrive, drop the files in `fonts/` and replace the `@import` line.

Scale runs 11px → 56px (`--t-xxs` to `--t-4xl`). The wordmark uses `--t-3xl` Pretendard 800. Headings are also Pretendard at 600–700. Korean is set in the *same* family — no pairing required — which keeps the visual rhythm calm.

### Spacing

10-step scale, 4 → 72 px (`--s-1` to `--s-10`). The system is generous: card padding starts at 24px (`--s-6`); buttons stretch to fill their container; vertical rhythm between sections is 24–32px.

### Backgrounds

The signature backdrop is a **soft vertical gradient from cream to sage**, with optional blurred cloud / leaf shapes drifting behind. Helpers in `colors_and_type.css`:

- `.bg-cream` — flat warm cream. Default page background.
- `.bg-gradient` — cream top fading into pale sage bottom, with a corner cream-warm highlight.
- `.bg-clouds` — the **hero / login backdrop**: cream + multiple blurred green blobs + a top-right white cloud highlight.
- `.screen` — the canonical app surface: a rounded-32px container clipped over the gradient, with a sage corner blob.

**No full-bleed photography. No stock garden photos. No hand-drawn illustrations.** When imagery is needed, it's the cloud SVG (`assets/cloud-bg.svg`), the leaf SVG (`assets/leaf.svg`), or a blurred coloured ellipse drawn in CSS. Imagery is soft, organic, and silent — never a focal point.

### Animation

The brief is **active animation** — *not flashy, but everything appears*. Pop, fade, slide. Every screen change should feel like the page settling.

- **Easing**: `--ease-out` (cubic-bezier(0.16, 1, 0.3, 1)) is the default. `--ease-soft` adds a tiny overshoot (1.16) for the green CTA press and the today-dot pop.
- **Durations**: `--dur-2` (240ms) hover/fade, `--dur-3` (380ms) slide-in/card appear, `--dur-4` (600ms) sequenced reveals.
- **Sequenced entry**: chat bubbles, calendar days, chips animate in with a 40–60ms stagger.
- **Keyframes**: `days-fade-in`, `days-rise`, `days-pop`, `days-slide-in`, `days-drift` (clouds), `days-dot-pulse`, `days-thinking` — all in `colors_and_type.css`.
- **The "Thinking…" indicator**: three sage dots pulsing in sequence inside an AI bubble. Never a spinner.
- **No parallax, no scroll-triggered surprises, no bouncing icons** beyond the gentle press.
- **The cloud-leaf logo gently drifts** on the login screen — `days-drift` 8s ease-in-out infinite, 8px amplitude.

### Hover, press, focus

- **Primary CTA (sage button)**: rest `--sage-leaf`. Hover slides one step deeper to `--sage-forest`. Press scales to 0.97 + inset shadow. Disabled is `--sage-mist` (the same green, washed out) — never grey.
- **Secondary CTA (outline / white pill)**: rest `--paper-pure` + 1px `--line` border. Hover background fades to `--paper-mist`, border stays.
- **Chip (interest tag)**: inactive is white with `--line` border. Active is `--sage-leaf` solid with white text. Toggle is instant; no transition.
- **Icon button**: opacity 0.7 → 1.0 on hover.
- **Press**: scale(0.97) + `--shadow-press`. No colour change.
- **Focus**: `--shadow-ring` — a 3px translucent sage ring. **Never** blue browser default.
- **Disabled**: opacity 0.5, no colour change, `cursor: not-allowed`.

### Borders

- **Default**: `1px solid var(--line)` — soft cool-grey `#DDDED0`.
- **Hairline**: `1px solid var(--line-faint)` — for dividers inside a card.
- **Emphasized**: `1.5px solid var(--sage-leaf)` — focused input, active chip border (when filled is too heavy).
- **No double borders. No outlines on filled buttons.** No coloured-left-border-accent cards — that's a SaaS cliché this brand refuses.

### Shadows

Four warm, low-saturation steps (rgba of `#364626`, not black):

- `--shadow-1` — barely-there lift (input on focus, chip).
- `--shadow-2` — default card shadow.
- `--shadow-3` — modal, dropdown, raised composer.
- `--shadow-card` — the soft drop on the phone-screen-shaped containers from the screenshots.
- `--shadow-ring` — focus ring (3px sage at 22% opacity).
- `--shadow-press` — inset for pressed state.

No coloured glows. No neon. The shadow feels like daylight from outside a window.

### Transparency & blur

- **AI chat bubble** sits on the sage-paper background at 100% white — no transparency. Its softness comes from radius (18px) and a barely-visible 4% sage border.
- **Modal scrim** is the cream gradient blurred and dimmed: `rgba(46, 59, 31, 0.18)` + `backdrop-filter: blur(6px)`. Always blurred — never a flat black scrim.
- Backgrounds with cloud SVGs use 0.85 opacity to let the gradient peek through.

### Corner radii

- Buttons: `--r-pill` (999px) for primary CTAs. `--r-3` (14px) for tertiary text buttons.
- Inputs / chips / pills: `--r-pill` for chips, `--r-4` (18px) for textarea / multiline.
- Cards / chat bubbles: `--r-5` (24px) — generous. Bubble has one squared corner indicating speaker (`6px 24px 24px 24px` for AI, `24px 6px 24px 24px` for user).
- The phone-screen container in mocks: `--r-6` (32px).
- Avatar: `--r-pill`.

### Card anatomy

A card in *Days* is:

- Background `--paper-pure` (white) on a sage-wash page, or `--paper-warm` cream on a cream page.
- 1px `--line` border, *or* no border + `--shadow-card`. Never both heavy.
- `--r-5` (24px) radius.
- `--shadow-card` (a soft warm drop).
- Inner padding `--s-6` (24px).
- Optional Korean label at top in `.t-label` style.

### Layout rules

- **Mobile-first.** The product is a phone app — every UI kit screen targets a 390×844 mobile viewport, and the web frame just hosts that phone screen centered with a sage backdrop.
- **One column.** Max content width 390px (mobile), 480px when displayed on desktop, 900px for marketing splash.
- **Vertical rhythm.** 24px between form sections, 32px between major sections.
- **8px grid baseline.** Every dimension snaps.
- **No split-screen layouts. No side-by-side feature columns.** The app reads top to bottom.

---

## ICONOGRAPHY

The brand uses **outline line icons** in 1.75px stroke, with rounded caps and joins, on a 24×24 grid. The deep sage color (`--ink-deep`) is the default; `--sage-leaf` is the active-state colour. The signature exception is the cloud-leaf logo mark, which is filled.

### What ships in this system

- **Cloud-leaf logo** — `assets/logo-cloud.svg` (outline, primary), `assets/logo-mark.svg` (filled, favicon/badge). The cloud shape is the brand container; the leaf inside reads as a stylized P (for the product code-name) but the visual cue is "a leaf grew inside a cloud".
- **Leaf** — `assets/leaf.svg` — a standalone teardrop leaf used decoratively (behind text, in onboarding background, as a small accent next to "Days").
- **Cloud background** — `assets/cloud-bg.svg` — soft white cloud silhouette for full-bleed background decoration.
- **Icon set** — `assets/icons/` — 20 single-color line icons covering the entire current product surface:
  - **Identity / form**: `user`, `lock`, `mail`, `cake` (age), `camera` (avatar edit), `bell` (notification time)
  - **Navigation**: `chevron-left`, `chevron-right`, `arrow-left`, `arrow-right`, `arrow-up` (send)
  - **Actions**: `plus`, `close`, `check`, `pencil` (edit), `settings`
  - **Concept**: `cloud`, `calendar`, `book` (diary), `sparkles` (AI generating)

### Approach

- **Real emoji for moods only.** The five mood faces (😊 😭 😠 😐 😩) are not icons — they're the product's content. Use the actual Unicode emoji, not custom SVG.
- **No decorative emoji** anywhere else.
- **No icon font.** SVG only — stroke and color are controllable per-icon.
- **No multi-color icons.** Selected state changes colour, never shape.
- **No filled UI icons.** Outline only. The logo mark is the lone exception (because at small sizes a filled cloud reads better than an outline).
- **Sized 18–24px** in UI. Avatar / cloud-mark badge can go larger (48–72px). Never under 14px.
- **`currentColor` stroke** — icons inherit colour from their parent so the same SVG works in `--ink-deep`, `--sage-leaf`, or `--paper-pure` (white-on-green).

### Substitution rule

If a new icon is needed and isn't in `assets/icons/`:
1. **Prefer** drawing one to match the existing set (1.75px stroke, rounded caps, 24×24, single colour).
2. **Fallback** to [Lucide](https://lucide.dev) — same stroke style, same grid. If you pull one in, restroke to 1.75px and recolour to `currentColor`.
3. **Flag the substitution** in the README of whatever artifact uses it.

---

*See `SKILL.md` for the agent-invocable summary.*
