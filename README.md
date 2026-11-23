# Orrery

**Your TouchDesigner parameters, on your phone.**

Orrery is a free phone remote for TouchDesigner. You don't draw a layout or map OSC addresses.
The parameters you already built become sliders, switches and buttons. Hand the phone to a
client, a VJ or the venue tech, and they can only touch what you chose to show.

There is no app to install. The component serves the remote itself: the phone scans a QR code
and opens it in its browser.

> **Status: early (v0.1).** Feedback and issues are welcome.

## Quick start

1. **Add the component.** Drag [`td/orrery.tox`](td/orrery.tox) into your project, next to the
   COMPs you want to control.
2. **Pick your controls.** On any of those COMPs, add a custom parameter page named
   **Controls** (right-click the COMP › Customize Component…). Put the parameters you want on
   the phone on that page.
3. **Pair the phone.** Press **Show QR** on the component's **Orrery** page and scan the code
   with the phone's camera. Or open the **Address** in the phone's browser and type the 6-digit
   **Pairing Code**.

That's it. The phone remembers the code, and changes made in TouchDesigner show up on the phone
right away. Add the page to the home screen to open it like an app.

The phone and the computer must be on the same network.

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

Sliders and steppers show **Reset** when the value is off its default. Any other parameter
type is shown as its value, read only. The phone shows each parameter's **Label**, so give it a
friendly one.

## Settings

All on the component's **Orrery** page:

| Parameter | Default | What it does |
|---|---|---|
| Active | on | runs the server |
| Show QR | | opens a QR code on this computer for the phone to scan |
| Address | | the page to open on the phone (read only) |
| Pairing Code | | the code the phone needs (read only) |
| New Pairing Code | | makes a new code and disconnects every phone |
| Phones Connected | | how many phones are paired now |
| Port | 9980 | change it if 9980 is taken |
| Controls In | `..` | the COMP whose children are listed |
| Page Name | Controls | the parameter page the remote reads |
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
- **No QR code?** The QR page needs the internet on the computer to draw it. The address and
  code are shown under it either way.
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
npm install && npm test                             # remote.html and pair.html in jsdom
```

`tests/td/tdfake.py` models only what the scripts touch (COMPs, custom pages, parameters, the
Web Server DAT). `tests/fixtures/synth_state.json` is what the Python side must produce and what
the remote's tests render, so the two halves can't drift apart. Some tests also check that
build.py, this README and [td/README.md](td/README.md) still agree.

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
