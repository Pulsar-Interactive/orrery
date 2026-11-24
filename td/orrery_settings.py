# Parameter Execute DAT `settings` inside the Orrery component, watching the component itself.
import random

def new_code(comp):
	comp.par.Code = '%06d' % random.SystemRandom().randrange(1000000)
	op('qrtop').cook(force=True)

def refresh(comp):
	m = op('callbacks').module
	comp.par.Address = m.address()
	pe = op('parexec')
	(pe.par.ops if hasattr(pe.par, 'ops') else pe.par.op).val = m.root().path + '/*'
	op('qrtop').cook(force=True)  # an open QR window follows a new address

def show_qr(comp):
	# Opens the QR in a TouchDesigner viewer window for a camera to scan. It is drawn inside the
	# component (Script TOP `qrtop`), so it needs no internet and is only shown on this screen.
	refresh(comp)
	qr = op('qrtop')
	qr.cook(force=True)
	qr.openViewer(unique=True)

def onValueChange(par, prev):
	if par.name in ('Port', 'Root', 'Page'):
		refresh(par.owner)
	if par.name in ('Root', 'Page', 'Onair', 'Record'):
		m = op('callbacks').module
		m.broadcast(m.listing())
	return

def onPulse(par):
	if par.name == 'Newcode':
		new_code(par.owner)
		# phones paired with the old code have to pair again
		server = op('server')
		server.par.active = False
		server.par.active = True
	elif par.name == 'Refresh':
		refresh(par.owner)
	elif par.name == 'Showqr':
		show_qr(par.owner)
	return
