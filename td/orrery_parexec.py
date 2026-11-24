# Parameter Execute DAT `parexec` inside the Orrery component, watching every COMP under Root.
# Sends a fresh state to every paired phone when a control changes, from the phone or in TouchDesigner,
# and a fresh list when that change moved what's on air (the component's On Air parameter).
def onValueChange(par, prev):
	m = op('callbacks').module
	if par.page and par.page.name == m.page_name() and m.controls_page(par.owner):
		m.broadcast(m.state(par.owner))
		m.check_live()
	return

def onPulse(par):
	return
