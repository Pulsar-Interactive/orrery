## TD Remote

Product: TD Remote, a phone remote for TouchDesigner: a drop-in .tox that serves its own web remote.
Repo `td-remote` (public).

- Web first (decided 2026-11-22): the component serves the remote itself, `td/remote.html`
  (one file, vanilla JS, no build), at `http://ADDRESS:PORT/`, for any device with a browser.
  Show QR opens the Script TOP `qrtop` in a viewer window: the QR is drawn inside the component
  by `td/td_remote_qr.py` (plain Python), so pairing works with no internet (decided 2026-11-24;
  it was a browser page loading a QR library from a CDN). Nothing to install, no stores. First tested live on 2026-11-22
  (a phone paired via QR).
- No native app. Build one only if people ask for what the browser can't do (haptics, a store
  listing).
- TouchDesigner: `td/*.py` + `td/*.html` → `td/build.py` → `td/td-remote.tox`. Rebuild after editing.
- Pairing: a 6-digit code in the WebSocket URL; unpaired clients get nothing.
- Never use "TouchDesigner" in the product name (Derivative's trademark).
- Free and MIT (decided 2026-11-21): no paid tier. Its value is visibility and leads for Pulsar. The name, icon and Pulsar logo are not licensed (README).
- Brand: the eclipse mark (decided 2026-11-23), files and rules in `assets/brand/`. The web
  pages carry it inline as data URIs; rebuild the .tox after changing them.
