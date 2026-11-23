## Orrery

Product: Orrery, a phone remote for TouchDesigner: a drop-in .tox that serves its own web remote.
Repo `orrery` (public; history rewritten 2026-11-22 without the Expo app).

- Web first (decided 2026-11-22): the component serves the remote itself, `td/remote.html`
  (one file, vanilla JS, no build), at `http://ADDRESS:PORT/`. Show QR opens `td/pair.html` on
  the computer as a local file. Nothing to install, no stores. First tested live on 2026-11-22
  (circle.155, a phone paired via QR).
- The Expo native app was removed on 2026-11-22 (in git history before that). Bring a native app
  back only if people ask for what the browser can't do (haptics, a store listing).
- TouchDesigner: `td/*.py` + `td/*.html` → `td/build.py` → `td/orrery.tox`. Rebuild after editing.
- Pairing: a 6-digit code in the WebSocket URL; unpaired clients get nothing.
- Never use "TouchDesigner" in the product name (Derivative's trademark).
- Free and MIT (decided 2026-11-21): no paid tier. Its value is visibility and leads for Pulsar. The name, icon and Pulsar logo are not licensed (README).
