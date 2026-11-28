# The TD Remote component

| Operator | Type | |
|---|---|---|
| `server` | Web Server DAT | port and active follow the component's Port and Active; serves the remote at `/`, the files in `assets` and the WebSocket |
| `remote` | Text DAT | [remote.html](remote.html): the phone remote, one page |
| `assets` | Table DAT | [web/](web): the app manifest, icons and Pulsar logo the page loads, as base64 (name, data) |
| `qr` | Text DAT | [td_remote_qr.py](td_remote_qr.py): a QR code encoder in plain Python, no modules, no internet |
| `qrtop` | Script TOP | callbacks [td_remote_qrtop.py](td_remote_qrtop.py): draws the pairing QR (address + code); Show QR opens it in a viewer window |
| `qrtop_callbacks` | Text DAT | [td_remote_qrtop.py](td_remote_qrtop.py): the Script TOP's callbacks (replaces the default one TouchDesigner docks to it) |
| `callbacks` | Text DAT | [td_remote_callbacks.py](td_remote_callbacks.py): pairing and the protocol |
| `parexec` | Parameter Execute DAT | [td_remote_parexec.py](td_remote_parexec.py): OPs `<Controls In>/*`, pushes changes to phones |
| `settings` | Parameter Execute DAT | [td_remote_settings.py](td_remote_settings.py): the component's own parameters, Show QR |
| `start` | Execute DAT | [td_remote_start.py](td_remote_start.py): address and first pairing code on start / load; re-checks the Setup page once a second |

The component has two parameter pages. **TD Remote** holds the settings (port, pairing, Show QR). **Setup**
is a checklist of what the phone needs, ticked by `settings.check_setup`: server running, COMPs next to
TD Remote, a Controls page (with a parameter on it) on one of them, and a paired phone. Next Step says what to do
about the first one that is missing, and Open the Guide opens https://tdremote.pulsarinteractive.ai/#how.

[build.py](build.py) creates all of it and saves `td-remote.tox`.

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
