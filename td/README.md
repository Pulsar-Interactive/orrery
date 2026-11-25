# The Orrery component

| Operator | Type | |
|---|---|---|
| `server` | Web Server DAT | port and active follow the component's Port and Active; serves the remote at `/`, the files in `assets` and the WebSocket |
| `remote` | Text DAT | [remote.html](remote.html): the phone remote, one page |
| `assets` | Table DAT | [web/](web): the app manifest, icons and Pulsar logo the page loads, as base64 (name, data) |
| `qr` | Text DAT | [orrery_qr.py](orrery_qr.py): a QR code encoder in plain Python, no modules, no internet |
| `qrtop` | Script TOP | callbacks [orrery_qrtop.py](orrery_qrtop.py): draws the pairing QR (address + code); Show QR opens it in a viewer window |
| `qrtop_callbacks` | Text DAT | [orrery_qrtop.py](orrery_qrtop.py): the Script TOP's callbacks (replaces the default one TouchDesigner docks to it) |
| `callbacks` | Text DAT | [orrery_callbacks.py](orrery_callbacks.py): pairing and the protocol |
| `parexec` | Parameter Execute DAT | [orrery_parexec.py](orrery_parexec.py): OPs `<Controls In>/*`, pushes changes to phones |
| `settings` | Parameter Execute DAT | [orrery_settings.py](orrery_settings.py): the component's own parameters, Show QR |
| `start` | Execute DAT | [orrery_start.py](orrery_start.py): address and first pairing code on start / load |

[build.py](build.py) creates all of it and saves `orrery.tox`.

## Protocol (JSON over WebSocket)

The phone opens `http://ADDRESS:PORT/` (or `/?code=CODE` from the QR, which the page saves and drops
from the address bar) and connects to `ws://ADDRESS:PORT/?code=CODE`. A wrong code gets `{"type": "denied"}` and is closed.

```
-> {"type": "list"}                       <- {"type": "list", "project", "live", "recording", "patches": [{"op", "label", "count", "canLive", "show"}]}
-> {"type": "live", "op": "synth"}        (sets the parameter On Air names; every phone gets a new list)
-> {"type": "record", "on": true}         (starts or stops the toggle Record names; every phone gets a new list)
-> {"type": "get", "op": "synth"}         <- {"type": "state", "op", "controls": [...]}
-> {"type": "set", "op", "par", "value"}  (Pulse parameters ignore value)
<- {"type": "error", "error": "..."}
```

A control is `{name, label, style, section, value?, options?, min?, max?, default?, readOnly?}`.
`section` is TouchDesigner's Start Section; `style: "Header"` starts a group. Read-only
parameters are shown, never set.
