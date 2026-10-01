# Chat — Ask Nakshion (`/chat`, `/chat/:conversationId`)

**User goal:** ask a personal question, get an answer that is clearly about *my* chart, quickly.
**Primary action:** Send (ai round IconButton). No gold on this screen.

## Layout

| | 375px | ≥768 | ≥1024 |
|---|---|---|---|
| Header | 56px: back/menu IconButton (opens history Sheet) · "Ask Nakshion" `text-title` · chart context chip ("Asha's chart ▾") · overflow menu (New chat, Delete) | same | header spans the main column only |
| History | Sheet from left (85% width) | Sheet | persistent sidebar 280px, `surface`, list rows 56px (title 1 line + relative time), active row `ai-subtle` + 3px `ai` bar, `New chat` secondary button at top, search field when > 10 conversations |
| Messages | full width, px-4, `max-w-chat` centred | px-6 | centred column `max-w-chat` |
| Composer | sticky bottom, safe-area aware, keyboard-aware | same | same, aligned to column |
| Bottom nav | **hidden** on this route (composer owns the bottom edge); back affordance in header | — | — |

Background: plain `bg` (no starfield, no nebula) — reading comfort (P1).

## Empty conversation
- Centred block (vertically ~35% from top): AI avatar lg + `text-h2` "What's on your mind, Asha?" + `text-body fg-secondary` "I'll answer from your chart — your Moon in Rohini, your Shani Mahadasha, today's transits."
- 4 suggestion Chips (2×2 on mobile, 1 row on ≥768), personalised: love, career, timing, today.
- Language Segmented under the chips on first visit only (EN · हिंदी · Hinglish), then lives in the composer menu.

## Conversation
- Message specs: COMPONENTS.md → ChatMessage. AI turns full-width editorial; user turns bubbles.
- **Streaming** is the target behaviour (today the whole answer arrives at once behind a typing indicator). Until the backend streams, use the "thinking" state with progressive copy; the component contract is identical so swapping to SSE needs no redesign.
- Day separators: "Today", "Yesterday", date — `text-caption fg-muted` centred with hairlines.
- Long answers: no collapse; headings inside AI markdown create scannability.
- Grounding Badges under every AI answer (P2). If the backend can't provide them yet, show one static Badge "Based on your chart" — never invent specifics.

## States
- Loading history: 3 skeleton message pairs.
- Send failed / interrupted / error: per ChatMessage state table.
- Rate limit / quota (premium tier): inline card above composer, `warning-subtle`: "You've used today's 10 questions. Resets at midnight." + `See Premium` secondary. Composer disabled with that reason as `aria-describedby`.
- Offline: composer note; queued message shown as "sending".

## Keyboard & a11y
- `/` focuses composer (when not typing). Esc stops generation. ↑ edits last message.
- Log region rules per COMPONENTS.md; sidebar is a `<nav aria-label="Conversations">`.

## Motion
User bubble spring in; AI fade; no stagger on history load; no parallax.
