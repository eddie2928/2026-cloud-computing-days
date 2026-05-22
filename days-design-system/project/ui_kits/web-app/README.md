# days · Web App UI Kit

A high-fidelity React recreation of the **days** web app — the only product surface in this design system.

Open `index.html` to step through all five screens as an interactive click-through prototype. No real backend; all state is local React state, just like in the live app's localStorage-backed demo mode.

## What's here

| File | Role |
|---|---|
| `index.html` | Entry point. Loads React + Babel + tokens + components. Hosts the demo router. |
| `app.jsx` | Top-level demo router — switches between Login, Today, QnA chat, Diary view, Calendar, Profile. Holds the mock "saved diaries" map. |
| `Logo.jsx` | The days wordmark mark (Playfair Display Italic + gold dot). |
| `Sidebar.jsx` | 220px fixed-width nav with three items: 오늘 쓰기 · 캘린더 · 프로필. |
| `Primitives.jsx` | `Button`, `TextField`, `DateField`, `Textarea`, `Eyebrow`, `Card`, `Icon`, `ThinkingDots`. |
| `ChatBubble.jsx` | AI + user chat bubbles, both shapes. |
| `CalendarMonth.jsx` | Month grid with empty / saved / today day states. |
| `screens/Login.jsx` | Password login. |
| `screens/Today.jsx` | Date picker + "begin" CTA. |
| `screens/QnAChat.jsx` | The five-question chat loop with sticky composer. |
| `screens/DiaryDone.jsx` | Generated diary reveal. |
| `screens/CalendarPage.jsx` | Month view, dots on saved days, click to read. |
| `screens/DiaryView.jsx` | Read a single past diary. |
| `screens/Profile.jsx` | Display name form. |

## Fidelity notes

- The five questions are **canned** (five hand-written Korean prompts that fit the brand voice). The real app generates these via Bedrock; for prototyping purposes a fixed list is enough.
- "Saved diaries" are seeded so the calendar has dots out of the box. Saving a new diary in the demo flow adds it to the in-memory map for the current session only.
- Cosmetics over correctness: the diary auto-generator is a placeholder string that reads naturally; we don't actually call an LLM.
- All animations live in `colors_and_type.css` and are applied per-screen.

## Component coverage

Covers buttons (primary / secondary / ghost / disabled), text + date + textarea inputs, sidebar nav with active state, chat bubbles, thinking-dot loader, calendar day states (empty / saved / today / streak), diary card with serif body, eyebrow labels, dotted-leader progress indicator, focus rings, hover wash, press states.

## Where the design comes from

The visual recreation is rooted in the source code's structure and copy (Korean labels, 5-question loop, sidebar order, sticky composer) but **not** its visual treatment — the source uses indigo + gray and a default system-ui stack. We reskinned per the brief: **light beige + gold, warm paper, lines & dots, gentle "appear" animation**. See the parent `README.md` for the full visual reasoning.
