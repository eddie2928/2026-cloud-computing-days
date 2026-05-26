# Days — Web App UI Kit

A pixel-faithful, click-through recreation of the Days product surface, derived from the brand reference screenshots and the upstream codebase contracts.

Open **`index.html`** to see all six screens connected as a live prototype.

## Structure

- `index.html` — host page with phone-frame scaffold, top-of-page nav, and the screen orchestrator.
- `app.jsx` — main `<App>` component; owns screen state + modal overlays.
- `styles.css` — phone-frame chrome + decorative backdrop blobs (everything else uses `colors_and_type.css` tokens).
- `Primitives.jsx` — shared building blocks: `Logo`, `CloudLeaf`, `Wordmark`, `Icon`, `PhoneFrame`, `PillButton`, `PillInput`, `BoxInput`, `Chip`, `FieldLabel`, `ProgressBar`, `SoftBackdrop`. Exposed via `window.DaysUI`.
- `screens/`
  - `Login.jsx` — Days wordmark + email/password + Google OAuth + forgot link
  - `Onboarding.jsx` — nickname / gender (segmented) / age / interests (chips) + Next CTA
  - `Calendar.jsx` — monthly view with the five mood emojis, today-ring on day 22, profile + settings header
  - `DiaryDetail.jsx` — modal with big mood emoji, inline picker, body, save
  - `Chat.jsx` — full-screen modal: AI 5-question Q&A, cloud avatar, sage user bubbles, thinking dots, progress, send pill
  - `Profile.jsx` — avatar + camera badge, fields, interest chips, notification time, save + logout

## What this UI kit is *not*

- It's not production code. There's no real backend, no real auth, no real AI.
- It's not a Storybook of every variant. It's the **canonical look** of each screen — one happy-path state. If you need other states (errors, empty calendars, etc.), build them on top of these primitives.
- It's not the source of truth for tokens — `../../colors_and_type.css` is.

## How to use it elsewhere

1. Link `colors_and_type.css` from the project root.
2. Copy `Primitives.jsx` (and whichever `screens/*.jsx` files you want) into your artifact's directory.
3. Load React 18.3.1 + ReactDOM + Babel standalone (see `index.html` for the exact pinned URLs).
4. The `<Icon>` component takes a `name` from the inlined `ICON_PATHS` map in `Primitives.jsx` — extend that map (or copy an SVG from `../../assets/icons/`) if you need a new glyph.

The phone frame itself is opinionated and lives in `styles.css` — if you're building a non-phone artifact, ignore `.phone*` classes and just render screens directly.
