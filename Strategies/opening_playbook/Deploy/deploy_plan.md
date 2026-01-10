# Deploy Plan — opening_playbook

## Scope
- Strategy: opening_playbook
- Mode: live (after DEPLOY gate passes)
- Universe: IPS-allowed, liquid only, catalyst + gap + premarket volume filters

## Risk / Controls
- Max size, max slippage, stop distance, time kill-switch enforced by guardrails + execution rules
- Kill switch triggers:
  - daily loss limit hit
  - max drawdown breach
  - repeated slippage anomalies
  - data feed / broker instability

## Rollout
1) Day 1–2: micro size (smallest live size)
2) Day 3–5: scale to normal size only if no incidents and metrics stable
3) Any incident → revert to micro / disable

## Rollback Plan
- Set registry enabled=false immediately
- Archive logs + incident notes
- Revert to previous known-good version

## Versioning
- version bump required for any logic change
