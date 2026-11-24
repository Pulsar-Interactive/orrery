# Callbacks for the Script TOP `qrtop` inside the Orrery component: draws the pairing QR (the
# address with the code in it) using the `qr` encoder, black on white with a quiet zone, so any
# camera can scan it off this screen. Show QR opens it in a viewer window.
import numpy

def onSetupParameters(scriptOp):
	return

def onCook(scriptOp):
	comp = parent()
	address, code = comp.par.Address.eval(), comp.par.Code.eval()
	m = op('qr').module.matrix('%s/?code=%s' % (address, code)) if address and code else []
	n, cell = len(m) + 8, 12  # 4 modules of white around it, 12 pixels a module
	a = numpy.full((n, n), 255, numpy.uint8)
	for y, row in enumerate(m):
		for x, dark in enumerate(row):
			if dark:
				a[y + 4, x + 4] = 0
	a = numpy.kron(a[::-1], numpy.ones((cell, cell), numpy.uint8))  # TouchDesigner rows start at the bottom
	scriptOp.copyNumpyArray(numpy.dstack([a, a, a, numpy.full_like(a, 255)]))
	return
