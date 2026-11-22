@AGENTS.md

## Orrery

Product: Orrery, a phone remote for TouchDesigner (public app, "Orrery, for TouchDesigner").
Repo `moon-orrery` (a moon: Pulsar's mobile app type). Seeded on 2026-11-21 from
`r&d/moon-touchdesigner`, which stays Pulsar's own show remote (autopilot, REC, on air) until
Orrery can replace it.

- Web first (decided 2026-11-22): the component serves the remote itself, `td/remote.html`
  (one file, vanilla JS, no build), at `http://ADDRESS:PORT/`. Show QR opens `td/pair.html` on
  the computer as a local file. Nothing to install, no stores. Tested against a mock server
  only until the .tox is built in TouchDesigner.
- Parked native app (Expo): `App.tsx` → `Connect.tsx` / `Remote.tsx`, `machines.ts`. Only
  revive it if people ask for what the browser can't do (haptics, a store listing).
- TouchDesigner: `td/*.py` + `td/*.html` → `td/build.py` → `td/orrery.tox`. Rebuild after editing.
- Pairing: a 6-digit code in the WebSocket URL; unpaired clients get nothing.
- Never use "TouchDesigner" in the product name (Derivative's trademark).
- Free and MIT (decided 2026-11-21): no paid tier. Its value is visibility and leads for Pulsar. The name, icon and Pulsar logo are not licensed (README).
