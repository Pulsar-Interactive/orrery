# Orrery

Control TouchDesigner from your phone. Orrery turns the parameters you already built into a
phone remote: no layouts to draw, no OSC addresses to map.

Every COMP with a custom parameter page named **Controls** shows up in the app, and every
parameter on that page becomes a control (sliders, toggles, menus, buttons). Header
parameters start a group. Nothing else in your project can be read or changed.

## Use it

1. Drag `td/orrery.tox` into your project, next to the COMPs you want to control.
2. On its **Orrery** page you'll find the **Address** and a 6-digit **Pairing Code**.
3. In the app, enter both and tap Connect. The phone remembers the machine.

Phone and computer must be on the same network. **New Pairing Code** disconnects every phone.

Settings on the Orrery page:

| Parameter | Default | |
|---|---|---|
| Active | on | runs the server |
| Port | 9980 | |
| Controls In | `..` | the COMP whose children are listed |
| Page Name | Controls | the parameter page the app reads |

## Develop

```bash
npm install
npx expo start        # scan with Expo Go
npm run typecheck && npx expo lint
```

The TouchDesigner component is built from the Python files in `td/`. After changing them, run
in TouchDesigner's Textport (with any project open):

```python
exec(open('/path/to/moon-orrery/td/build.py').read(), {'TD_DIR': '/path/to/moon-orrery/td'})
```

It builds `/project1/orrery` and saves `td/orrery.tox` (without a pairing code; each project
makes its own). See [td/README.md](td/README.md) for the protocol.

## License

Free and open source under the [MIT License](LICENSE): use it in personal and commercial work,
change it, share it.

The license covers the code, not the brand. The name "Orrery", the Orrery icon and the Pulsar
Interactive name and logo are not licensed for reuse: a fork or a published copy of the app needs
its own name and icon.

---

Made by [Pulsar Interactive](https://pulsarinteractive.ai). TouchDesigner is a trademark of
Derivative; Orrery is not affiliated with Derivative.
