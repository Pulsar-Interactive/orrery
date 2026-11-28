# TD Remote brand assets

The TD Remote mark: an eclipse, a planet passing in front of its sun. Two solid shapes, chosen
because they stay readable down to a 16 px favicon. Design canvas:
https://claude.ai/artifact/VGnG2Y5Tx4mx2mVgb42G8S

| File | Use |
|---|---|
| `td-remote-mark.svg` | Dark surfaces, 48 px and up. Carries the horizontal glitch slice from the Pulsar 'P'. |
| `td-remote-mark-light.svg` | Light surfaces. |
| `td-remote-mark-mono.svg` | One colour (`currentColor`), no glitch. Use below 48 px and inside UI. |
| `td-remote-icon.svg` | Rounded app tile, source for the icons in `td/web/`. |
| `pulsar-wordmark-black.svg` | Pulsar Interactive's wordmark for light surfaces (the white one is `td/web/pulsar.svg`). Footer of the root README. |
| `td-remote-card.png` | 1200 × 630 card: mark, wordmark, "Control TouchDesigner from your phone." Header of the root README; the same card is the website's social preview. |

- Below 48 px drop the glitch slice.
- Wordmark: **TD REMOTE** in Space Grotesk Bold, tracked +8% or wider. Endorsement line: "by Pulsar Interactive".
- Fonts: Space Grotesk (display, labels) + Inter (body), as in the Pulsar brand.
- The name and the mark are not covered by the MIT license (see the root README).

The phone remote's favicon and home-screen icons (`td/web/`, served by the component) and the
mark in its header (inline in `td/remote.html`) are rendered from these SVGs.
- Colours: Void `#111114` (ground), Sol Amber `#FFB020` (brand, primary action), cyan `#05F9FE`
  (selection, the one accent), off-white `#E8EDEF` (the mark's bodies).
