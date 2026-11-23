# Builds the Orrery component from the files next to this script and saves it as orrery.tox.
# Run it in TouchDesigner's Textport:
#   exec(open('/path/to/orrery/td/build.py').read(), dict(globals(), TD_DIR='/path/to/orrery/td'))
# It replaces /project1/orrery if there is one. Drag td/orrery.tox into any project to use it.
import os

src = TD_DIR  # noqa: F821 (passed in by the exec call above)
home = op('/project1')

def text(name):
	with open(os.path.join(src, name), encoding='utf-8') as f:
		return f.read()

old = home.op('orrery')
if old:
	old.destroy()
comp = home.create(baseCOMP, 'orrery')
comp.nodeX, comp.nodeY = 0, -400
comp.color = (0.31, 0.83, 0.87)
comp.comment = 'Orrery: control this project from a phone. Pair with the address and code on its Orrery page.'

page = comp.appendCustomPage('Orrery')
page.appendToggle('Active', label='Active')[0].default = True
page.appendPulse('Showqr', label='Show QR')
p = page.appendStr('Address', label='Address')[0]
p.readOnly = True
p = page.appendStr('Code', label='Pairing Code')[0]
p.readOnly = True
page.appendPulse('Newcode', label='New Pairing Code')
p = page.appendInt('Phones', label='Phones Connected')[0]
p.readOnly = True
p = page.appendInt('Port', label='Port')[0]
p.default, p.normMin, p.normMax, p.min, p.clampMin = 9980, 1024, 65535, 1024, True
page.appendCOMP('Root', label='Controls In')[0].default = '..'
page.appendStr('Page', label='Page Name')[0].default = 'Controls'
page.appendStr('Onair', label='On Air')  # optional: an expression naming the COMP on air
page.appendPulse('Refresh', label='Refresh Address')
for p in page.pars:
	if p.style not in ('Pulse',) and not p.readOnly:
		p.val = p.default
comp.par.Root = '..'

def ops_par(d):
	# the Parameter Execute DAT's OPs parameter
	return d.par.ops if hasattr(d.par, 'ops') else d.par.op

cb = comp.create(textDAT, 'callbacks')
cb.text = text('orrery_callbacks.py')
cb.nodeX, cb.nodeY = 0, 0

# the phone remote, served at http://ADDRESS:PORT/
rp = comp.create(textDAT, 'remote')
rp.text = text('remote.html')
rp.nodeX, rp.nodeY = 0, 150

# the QR page Show QR opens on this computer
pp = comp.create(textDAT, 'pairpage')
pp.text = text('pair.html')
pp.nodeX, pp.nodeY = 200, 150

server = comp.create(webserverDAT, 'server')
server.par.callbacks = 'callbacks'
server.par.port.expr = "parent().par.Port"
server.par.active.expr = "parent().par.Active"
server.nodeX, server.nodeY = 200, 0

pe = comp.create(parameterexecuteDAT, 'parexec')
pe.text = text('orrery_parexec.py')
pe.par.pars = '*'
pe.par.valuechange = True
pe.par.onpulse = False
pe.nodeX, pe.nodeY = 0, -150

st = comp.create(parameterexecuteDAT, 'settings')
st.text = text('orrery_settings.py')
ops_par(st).val = '..'
st.par.pars = 'Port Root Page Onair Newcode Refresh Showqr'
st.par.valuechange = True
st.par.onpulse = True
st.nodeX, st.nodeY = 200, -150

ex = comp.create(executeDAT, 'start')
ex.text = text('orrery_start.py')
ex.par.start = True
ex.par.create = True
ex.nodeX, ex.nodeY = 400, -150

# Saved without a pairing code: each project that loads the .tox makes its own (start / onCreate).
tox = os.path.join(src, 'orrery.tox')
comp.par.Code = ''
comp.unstore('*')
comp.save(tox)
ex.module.onStart()
print('Orrery built and saved to %s. Open %s on a phone and enter %s, or press Show QR.' % (tox, comp.par.Address, comp.par.Code))
