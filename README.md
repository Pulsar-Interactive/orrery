# Orrery

**Your TouchDesigner parameters, on your phone.**

Orrery is a free phone remote for TouchDesigner. You don't draw a layout or map OSC addresses.
The parameters you already built become sliders, switches and buttons. Hand the phone to a
client, a VJ or the venue tech, and they can only touch what you chose to show.

There is no app to install, and any device with a browser can connect: a phone, a tablet or a
laptop. The component serves the remote itself and draws its own QR code, so pairing needs no
internet: scan the code with the camera and the remote opens in the browser.

> **Status: early (v0.1).** Feedback and issues are welcome.

## Quick start

1. **Add the component.** Drag [`td/orrery.tox`](td/orrery.tox) into your project, next to the
   COMPs you want to control.
2. **Pick your controls.** On any of those COMPs, add a custom parameter page named
   **Controls** (right-click the COMP › Customize Component…). Put the parameters you want on
   the phone on that page.
3. **Pair the phone.** Press **Show QR** on the component's **Orrery** page: a window opens
   with the QR code. Scan it with the phone's camera. Or open the **Address** in any browser
   and type the 6-digit **Pairing Code**.

That's it. The phone remembers the code, and changes made in TouchDesigner show up on the phone
right away. Add the page to the home screen to open it like an app: in Safari, Share → **Add to
Home Screen** (it opens full screen, with the Orrery icon); in Chrome, ⋮ → **Add to Home screen**.
The app opens the Address it was added from, so if the computer's address changes, add it again
(or give the computer a fixed address on the router). An app added this way keeps its own
memory, so it asks for the Pairing Code once.

The phone and the computer must be on the same network.

Prefer a guide? Paste [SETUP.md](SETUP.md) into Claude or ChatGPT: it asks what you want on the
phone and writes the Textport script that builds the Controls page.

## What becomes what

| Parameter on the Controls page | On the phone |
|---|---|
| Float | slider across the parameter's range |
| Int | − / + stepper |
| Toggle | switch |
| Momentary | button you hold |
| Pulse | button you tap |
| Menu, String Menu | row of choices |
| Header | a group title for the parameters after it |
| Read-only parameter | shown, can't be changed |

Sliders move by how far you drag sideways, so scrolling past one or tapping it never changes
it. After you move a slider or stepper away from its default, it shows **Reset**. Choosing from
a menu or pressing Reset shows **Undo** for a few seconds. When the phone loses TouchDesigner,
it says so and locks every control until it reconnects, so the screen never shows a change
that didn't happen. Any other parameter type is shown as its value, read only. The phone shows
each parameter's **Label**, and each COMP's name with `_` as spaces, so give them friendly ones.

## Settings

All on the component's **Orrery** page:

| Parameter | Default | What it does |
|---|---|---|
| Active | on | runs the server |
| Show QR | | opens a window with the pairing QR code, drawn by the component (no internet needed) |
| Address | | the page to open on the phone (read only) |
| Pairing Code | | the code the phone needs (read only) |
| New Pairing Code | | makes a new code and disconnects every phone |
| Phones Connected | | how many phones are paired now |
| Port | 9980 | change it if 9980 is taken |
| Controls In | `..` | the COMP whose children are listed |
| Page Name | Controls | the parameter page the remote reads |
| On Air | | optional: an expression that returns the name of the COMP on air, e.g. `op('show').par.Patch`; the phone marks it ON AIR. When it names a parameter like that, each patch's screen gets a GO LIVE button that sets it |
| Record | | optional: an expression naming a recording Toggle, e.g. `op('recorder').par.Record`; every patch's screen gets a REC button next to GO LIVE, pinned to the top |
| Refresh Address | | reads the address again after you change networks |

## Safe to hand over

- A phone needs the pairing code. Without it, it can't see or change anything.
- Only parameters on a **Controls** page can be read or changed. The rest of the project is
  invisible to the remote.
- **New Pairing Code** locks out every phone at once, for example after a show.
- Each project that loads the `.tox` makes its own code.

## Can't connect?

- **Same network?** The phone and the computer must be on the same Wi-Fi. Guest and venue
  networks often block devices from reaching each other. A phone hotspot works.
- **Firewall?** On macOS, allow TouchDesigner to accept incoming connections.
- **Address changed?** Press **Refresh Address** (or **Show QR** again) after changing networks.
- **Too much in the list?** Add the tag `orrery-hide` to a COMP (Common page › Tags) to keep it off the phone.
- **Show-wide controls mixed in with the patches?** Tag a COMP `orrery-show` (sound input, playlist, autopilot…):
  it moves to a **SHOW** section at the top of the list, apart from the patches.
- **Nothing in the list?** The remote only lists COMPs next to the component that have a page named
  exactly **Controls** (or whatever **Page Name** says).

## Develop

Everything lives in `td/`: the phone remote is one HTML file (`remote.html`, no build step), the
rest is the component's Python. After changing anything there, rebuild the component in
TouchDesigner's Textport (any project open):

```python
exec(open('/path/to/orrery/td/build.py').read(), dict(globals(), TD_DIR='/path/to/orrery/td'))
```

It builds `/project1/orrery` and saves `td/orrery.tox`. The protocol is plain JSON over a
WebSocket, documented in [td/README.md](td/README.md), so you can write your own client.

### Tests

Neither suite needs TouchDesigner:

```sh
pip install -r tests/requirements.txt && pytest   # td/*.py against a fake TouchDesigner
npm install && npm test                             # remote.html in jsdom
```

`tests/td/tdfake.py` models only what the scripts touch (COMPs, custom pages, parameters, the
Web Server DAT, the Script TOP that draws the QR). Every QR the component draws is decoded back
with an independent reader (zxing-cpp). `tests/fixtures/synth_state.json` is what the Python side
must produce and what the remote's tests render, so the two halves can't drift apart. Some tests
also check that build.py, this README and [td/README.md](td/README.md) still agree.

GitHub Actions runs both suites on every pull request, and fails one that changes what goes into
the component without committing a rebuilt `td/orrery.tox`. Pushing a tag like `v0.1.0` (on
master) runs them again and publishes a release with `orrery.tox` attached, which is what the
download link points at.

Issues and pull requests are welcome.

## License

Free and open source under the [MIT License](LICENSE): use it in personal and commercial work,
change it, share it.

The license covers the code, not the brand. The name "Orrery", the Orrery icon and the Pulsar
Interactive name and logo are not licensed for reuse: a fork or a published copy needs
its own name and icon.

---

Made by [Pulsar Interactive](https://pulsarinteractive.ai), who build interactive shows and
installations. TouchDesigner is a trademark of Derivative; Orrery is not affiliated with
Derivative.
