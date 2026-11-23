# Orrery brand assets

The Orrery mark: an eclipse, a planet passing in front of its sun. Two solid shapes, chosen
because they stay readable down to a 16 px favicon. Design canvas:
https://claude.ai/artifact/VGnG2Y5Tx4mx2mVgb42G8S

| File | Use |
|---|---|
| `orrery-mark.svg` | Dark surfaces, 48 px and up. Carries the horizontal glitch slice from the Pulsar 'P'. |
| `orrery-mark-light.svg` | Light surfaces. |
| `orrery-mark-mono.svg` | One colour (`currentColor`), no glitch. Use below 48 px and inside UI. |
| `orrery-icon.svg` | Rounded app tile, source for the icons in `assets/`. |

- Below 48 px drop the glitch slice.
- Wordmark: **ORRERY** in Space Grotesk Bold, tracked +8% or wider. Endorsement line: "by Pulsar Interactive".
- Fonts: Space Grotesk (display, labels) + Inter (body), as in the Pulsar brand.
- The name and the mark are not covered by the MIT license (see the root README).

The data-URI favicon, home-screen icon and header mark in `td/remote.html` and `td/pair.html` are
rendered from these SVGs.
