# Execute DAT `start` inside the Orrery component: fills in the address and a first pairing code,
# and re-checks the Setup page once a second.
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

def onFrameEnd(frame):
	if frame % 60 == 0:
		op('settings').module.check_setup(parent())
	return
