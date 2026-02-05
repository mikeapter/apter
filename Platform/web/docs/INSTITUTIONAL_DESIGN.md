# Institutional Design Framework (Apter / BotTrader UI)

This project follows an institutional dashboard standard (Bloomberg-inspired). The UI prioritizes control, clarity, and information density.

## Non-negotiables
- Dense yet readable information
- Calm palette; no neon; no gradients; no glow; no blur effects
- No gamification, celebration, “winning” language, or emotional labels
- Hierarchy beats decoration (labels, values, then controls)

## Color rules
- Background: charcoal (not pure black)
- Text: off-white / light gray
- Accent colors are **muted** and reserved for state:
  - Risk-On: muted green
  - Neutral: muted amber
  - Risk-Off: muted red

## Typography rules
- Use neutral sans-serif for all UI text
- Monospace is **only** for tickers and timestamps
- Tight line-height; small type; consistent spacing

## Implementation notes
- Tokens live in: `app/globals.css`
- Tailwind theme maps to tokens in: `tailwind.config.ts`
- Utility primitives:
  - `.bt-panel`, `.bt-button`, `.bt-input`
  - `.bt-chip` with state variants
