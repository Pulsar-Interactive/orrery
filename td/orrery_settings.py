# Parameter Execute DAT `settings` inside the Orrery component, watching the component itself.
import random

# The explanation the Help button opens: the landing page's How it works section.
HELP_URL = 'https://orrery.pulsarinteractive.ai/#how'

def new_code(comp):
	comp.par.Code = '%06d' % random.SystemRandom().randrange(1000000)
	op('qrtop').cook(force=True)

def check_setup(comp):
	# Ticks the Setup page's checkboxes and says what to do next. Cheap: the `start` DAT runs it once a second.
	m = op('callbacks').module
	page = m.page_name()
	neighbours = [o for o in m.root().children if o.isCOMP and o != comp]
	shown = m.comps()
	checks = [
		('Okserver', bool(op('server').par.active.eval()), 'Turn Active on, so a phone can reach this component.'),
		('Okcomps', bool(neighbours), 'Put a COMP next to Orrery, or point Controls In at the network that has your COMPs.'),
		('Okpage', bool(shown), 'Add a custom parameter page named %s, with a parameter on it, to a COMP (right-click it, Customize Component).' % page),
		('Okphone', comp.par.Phones.eval() > 0, 'Press Show QR and scan it with a phone.'),
	]
	for name, ok, _ in checks:
		par = getattr(comp.par, name)
		if bool(par.eval()) != ok:
			par.val = ok
	todo = next((hint for _, ok, hint in checks if not ok), 'Everything is set. Phones can control this project.')
	if comp.par.Nextstep.eval() != todo:
		comp.par.Nextstep = todo
	if comp.par.Guide.eval() != HELP_URL:
		comp.par.Guide = HELP_URL

def refresh(comp):
	m = op('callbacks').module
	comp.par.Address = m.address()
	pe = op('parexec')
	(pe.par.ops if hasattr(pe.par, 'ops') else pe.par.op).val = m.root().path + '/*'
	op('qrtop').cook(force=True)  # an open QR window follows a new address
	check_setup(comp)

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
	elif par.name == 'Checksetup':
		check_setup(par.owner)
	elif par.name == 'Help':
		ui.viewFile(HELP_URL)  # opens the link in the default browser
	return
