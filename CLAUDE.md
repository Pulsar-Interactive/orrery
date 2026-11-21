@AGENTS.md

## Orrery

Product: Orrery, a phone remote for TouchDesigner (public app, "Orrery, for TouchDesigner").
Repo `moon-orrery` (a moon: Pulsar's mobile app type). Seeded on 2026-11-21 from
`r&d/moon-touchdesigner`, which stays Pulsar's own show remote (autopilot, REC, on air) until
Orrery can replace it.

- App: `App.tsx` (shell) → `Connect.tsx` (paired machines in `expo-sqlite/kv-store`, see
  `machines.ts`) or `Remote.tsx` (list + controls). Dark only (`theme.ts`), Pulsar fonts.
- TouchDesigner: `td/*.py` → `td/build.py` → `td/orrery.tox`. Rebuild the .tox after editing.
- Pairing: a 6-digit code in the WebSocket URL; unpaired clients get nothing.
- Never use "TouchDesigner" in the product name (Derivative's trademark).
- Free and MIT (decided 2026-11-21): no paid tier. Its value is visibility and leads for Pulsar. The name, icon and Pulsar logo are not licensed (README).
