# Parameter Execute DAT `settings` inside the Orrery component, watching the component itself.
import os
import random
import tempfile
import webbrowser

def new_code(comp):
	comp.par.Code = '%06d' % random.SystemRandom().randrange(1000000)

def refresh(comp):
	m = op('callbacks').module
	comp.par.Address = m.address()
	pe = op('parexec')
	(pe.par.ops if hasattr(pe.par, 'ops') else pe.par.op).val = m.root().path + '/*'

def show_qr(comp):
	# Opens a page on this computer with a QR code the phone's camera can scan. The page is a
	# local file, never served, so the code is only shown on this screen.
	refresh(comp)
	address, code = comp.par.Address.eval(), comp.par.Code.eval()
	html = (op('pairpage').text
		.replace('{{URL}}', '%s/?code=%s' % (address, code))
		.replace('{{ADDRESS}}', address)
		.replace('{{CODE}}', code))
	path = os.path.join(tempfile.gettempdir(), 'orrery-pair.html')
	with open(path, 'w', encoding='utf-8') as f:
		f.write(html)
	webbrowser.open('file://' + path)

def onValueChange(par, prev):
	if par.name in ('Port', 'Root', 'Page'):
		refresh(par.owner)
	if par.name in ('Root', 'Page', 'Onair'):
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
