# The Orrery component

| Operator | Type | |
|---|---|---|
| `server` | Web Server DAT | port and active follow the component's Port and Active; serves the remote at `/` and the WebSocket |
| `remote` | Text DAT | [remote.html](remote.html): the phone remote, one page |
| `pairpage` | Text DAT | [pair.html](pair.html): the QR page Show QR opens on this computer (a local file, never served) |
| `callbacks` | Text DAT | [orrery_callbacks.py](orrery_callbacks.py): pairing and the protocol |
| `parexec` | Parameter Execute DAT | [orrery_parexec.py](orrery_parexec.py): OPs `<Controls In>/*`, pushes changes to phones |
| `settings` | Parameter Execute DAT | [orrery_settings.py](orrery_settings.py): the component's own parameters, Show QR |
| `start` | Execute DAT | [orrery_start.py](orrery_start.py): address and first pairing code on start / load |

[build.py](build.py) creates all of it and saves `orrery.tox`.

## Protocol (JSON over WebSocket)

The phone opens `http://ADDRESS:PORT/` (or `/?code=CODE` from the QR, which the page saves and drops
from the address bar) and connects to `ws://ADDRESS:PORT/?code=CODE`. A wrong code gets `{"type": "denied"}` and is closed.

```
-> {"type": "list"}                       <- {"type": "list", "project", "patches": [{"op", "label", "count"}]}
-> {"type": "get", "op": "synth"}         <- {"type": "state", "op", "controls": [...]}
-> {"type": "set", "op", "par", "value"}  (Pulse parameters ignore value)
<- {"type": "error", "error": "..."}
```

A control is `{name, label, style, section, value?, options?, min?, max?, default?, readOnly?}`.
`section` is TouchDesigner's Start Section; `style: "Header"` starts a group. Read-only
parameters are shown, never set.
