# TD Remote setup guide (for AI assistants)

You are helping someone set up **TD Remote**, a free, open-source (MIT) remote for TouchDesigner.
A component, `td-remote.tox`, serves a web page that turns the parameters on a COMP's **Controls**
page into sliders, switches and buttons. Any phone, tablet or laptop on the same network opens
it in its browser. There is no app and no account.

Work through it with them one step at a time. Ask before assuming. Use plain words: the person
may know TouchDesigner well or barely.

## 1. Add the component

1. Download [td-remote.tox](https://github.com/Pulsar-Interactive/tdremote/releases/latest/download/td-remote.tox).
2. Drag it into the network **next to** the COMPs they want to control (same parent). The
   component lists the COMPs beside it; change its **Controls In** parameter to point elsewhere.

## 2. Choose what goes on the phone

Ask:

- Which COMP should appear on the phone? (Its name is shown with `_` as spaces, so
  `synth_main` shows as "synth main". Suggest renaming it if the name is cryptic.)
- Which parameters, inside that COMP, should the person holding the phone be able to change?
  Get the operator and parameter for each one (for example `noise1` › Period). If they don't
  know the parameter's Python name, tell them to hover the parameter and read it from the
  tooltip, or middle-click the operator.
- For each number: what range makes sense on a slider? (Narrower is safer for a client.)

Then write the Textport script below for them.

## 3. The Textport script

It adds a page named **Controls** to the COMP, one custom parameter per control, and binds the
real parameter to it, so moving a slider on the phone moves the real parameter. Running it again
updates the page instead of duplicating it.

Rules you must follow when filling it in:

- A custom parameter **name** starts with one uppercase letter, then only lowercase letters and
  digits: `Speed`, `Glow2`. Not `speed`, `GlowAmount` or `glow_amount`. The **label** can be
  anything; it's what the phone shows.
- Kinds: `float` (slider), `int` (− / + stepper), `toggle` (switch), `menu` (row of choices),
  `pulse` (button you tap), `header` (a group title on the phone).
- The target is `'operator/parameter'`, relative to the COMP.

```python
# TD Remote: build the Controls page on one COMP. Edit COMP and CONTROLS, then paste in the Textport
# (Dialogs › Textport and DATs) and press Enter.
COMP = op('/project1/synth')
CONTROLS = [
	# (name, label, kind, target 'operator/parameter', extra)
	('Look',    'Look',    'header', None, None),
	('Speed',   'Speed',   'float',  'noise1/period', (0.1, 4.0)),   # extra: (min, max)
	('Count',   'Count',   'int',    'copy1/ncy', (1, 12)),
	('Strobe',  'Strobe',  'toggle', 'level1/bypass', None),
	('Palette', 'Palette', 'menu',   'switch1/index', ['Dusk', 'Neon', 'Ice']),  # extra: choice labels; drives an integer index
	('Drop',    'Drop',    'pulse',  'trigger1/triggerpulse', None),
]

page = next((p for p in COMP.customPages if p.name == 'Controls'), None) or COMP.appendCustomPage('Controls')
pulses = []
for name, label, kind, target, extra in CONTROLS:
	old = getattr(COMP.par, name, None)
	if old is not None:
		old.destroy()
	t = None
	if target:
		o, pn = target.rsplit('/', 1)
		t = getattr(COMP.op(o).par, pn)
	if kind == 'header':
		page.appendHeader(name, label=label)
		continue
	if kind == 'float':
		p = page.appendFloat(name, label=label)[0]
		p.normMin, p.normMax = extra
		p.default = p.val = t.eval()
	elif kind == 'int':
		p = page.appendInt(name, label=label)[0]
		p.normMin, p.normMax = extra
		p.min, p.max, p.clampMin, p.clampMax = extra[0], extra[1], True, True
		p.default = p.val = t.eval()
	elif kind == 'toggle':
		p = page.appendToggle(name, label=label)[0]
		p.default = p.val = bool(t.eval())
	elif kind == 'menu':
		p = page.appendMenu(name, label=label)[0]
		p.menuNames = [str(i) for i in range(len(extra))]
		p.menuLabels = extra
		p.val = str(int(t.eval()))
		t.expr = "op('%s').par.%s.menuIndex" % (COMP.path, name)
		continue
	elif kind == 'pulse':
		page.appendPulse(name, label=label)
		pulses.append((name, target))
		continue
	t.bindExpr = "op('%s').par.%s" % (COMP.path, name)
	t.mode = ParMode.BIND

# pulses can't be bound: a Parameter Execute DAT inside the COMP passes each one on
pe = COMP.op('td_remote_pulses')
if pe:
	pe.destroy()
if pulses:
	pe = COMP.create(parameterexecuteDAT, 'td_remote_pulses')
	(pe.par.ops if hasattr(pe.par, 'ops') else pe.par.op).val = COMP.path
	pe.par.pars = ' '.join(n for n, _ in pulses)
	pe.par.valuechange, pe.par.onpulse = False, True
	pe.text = 'TARGETS = %r\ndef onPulse(par):\n\to, p = TARGETS[par.name].rsplit("/", 1)\n\tgetattr(parent().op(o).par, p).pulse()\n' % dict(pulses)
print('Controls page ready on', COMP.path)
```

Adapt it: drop the kinds they don't need, and if a target is a menu parameter rather than an
integer index, use `.eval()` instead of `.menuIndex` in that expression and give the Controls
menu the same menu names as the target.
If something errors, read the message with them; the usual causes are a wrong operator or
parameter name, or a custom parameter name that breaks the rule above.

## 4. Pair a device

1. Select the TD Remote component and open its **TD Remote** parameter page.
2. Press **Show QR**. A window opens with a QR code (drawn by the component, no internet needed).
3. Scan it with the phone's camera and open the link. The remote opens in the browser and
   remembers the pairing.

Or open the **Address** shown on that page in any browser and type the 6-digit **Pairing Code**.
Add the page to the home screen to open it like an app. **New Pairing Code** locks out every
device at once, for example after a show.

## Troubleshooting

Go through these in order:

1. **Same network?** The device and the computer must be on the same Wi-Fi. Guest and venue
   networks often block devices from reaching each other; a phone hotspot works.
2. **Firewall?** On macOS, allow TouchDesigner to accept incoming connections (System Settings ›
   Network › Firewall). On Windows, allow it on private networks.
3. **Address changed?** After changing networks, press **Refresh Address** (or **Show QR** again).
4. **Port taken?** Change **Port** (default 9980) and pair again.
5. **Nothing in the list?** Only COMPs next to the component (or in **Controls In**) with a page
   named exactly **Controls** (or whatever **Page Name** says) are listed.
6. **Too much in the list?** Add the tag `td-remote-hide` to a COMP (Common page › Tags).
7. **A control doesn't move the real parameter?** Check that the target parameter shows a bind
   or expression to the Controls parameter (a purple or blue field), and that nothing else
   overrides it, such as an export from a CHOP.

More detail: the [README](https://github.com/Pulsar-Interactive/tdremote#readme).
