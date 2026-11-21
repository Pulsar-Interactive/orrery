# Parameter Execute DAT `settings` inside the Orrery component, watching the component itself.
import random

def new_code(comp):
	comp.par.Code = '%06d' % random.SystemRandom().randrange(1000000)

def refresh(comp):
	m = op('callbacks').module
	comp.par.Address = m.address()
	pe = op('parexec')
	(pe.par.ops if hasattr(pe.par, 'ops') else pe.par.op).val = m.root().path + '/*'

def onValueChange(par, prev):
	if par.name in ('Port', 'Root', 'Page'):
		refresh(par.owner)
	if par.name in ('Root', 'Page'):
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
	return
