# Execute DAT `start` inside the Orrery component: fills in the address and a first pairing code.
def onStart():
	comp = parent()
	s = op('settings').module
	if not comp.par.Code.eval():
		s.new_code(comp)
	s.refresh(comp)
	return

def onCreate():
	onStart()
	return
