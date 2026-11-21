# Orrery: control TouchDesigner from a phone.
# Callbacks DAT of the Web Server DAT `server` inside the Orrery component.
#
# Every COMP next to the component (its Root parameter) that has a custom parameter page named
# like the component's Page parameter (default "Controls") shows up in the app, and every
# parameter on that page becomes a control. Nothing else in the project can be read or changed.
#
# A phone connects to ws://ADDRESS:PORT/?code=CODE. A wrong code gets {"type": "denied"} and is
# closed; nothing is sent to or accepted from it.
#
# Messages (JSON):
#   -> {"type": "list"}                       <- {"type": "list", "project", "patches": [{"op", "label", "count"}]}
#   -> {"type": "get", "op": "synth"}         <- {"type": "state", "op", "controls": [...]}
#   -> {"type": "set", "op", "par", "value"}  (Pulse parameters ignore value)
#   <- {"type": "error", "error": "..."}
# `parexec` pushes a fresh "state" to every paired phone when a control changes in TouchDesigner.
import hmac
import json
import socket
from urllib.parse import parse_qs, urlparse

def me_comp():
	return parent()

def page_name():
	return me_comp().par.Page.eval() or 'Controls'

def root():
	return me_comp().par.Root.eval() or me_comp().parent()

def controls_page(o):
	if o is None or not o.isCOMP or o == me_comp():
		return None
	name = page_name()
	return next((p for p in o.customPages if p.name == name), None)

def comps():
	return [o for o in root().children if controls_page(o)]

def find(name):
	o = root().op(str(name))
	if o is None or o.parent() != root() or not controls_page(o):
		raise ValueError('nothing to control called %s' % name)
	return o

def describe(par):
	d = {'name': par.name, 'label': par.label, 'style': par.style, 'section': par.startSection}
	if par.readOnly:
		d['readOnly'] = True
	if par.style not in ('Pulse', 'Momentary', 'Header'):
		v = par.eval()
		d['value'] = v if isinstance(v, (bool, int, float, str)) else str(v)
	if par.style in ('Menu', 'StrMenu'):
		d['options'] = [[n, l] for n, l in zip(par.menuNames, par.menuLabels)]
	if par.style in ('Float', 'Int'):
		d['min'], d['max'], d['default'] = par.normMin, par.normMax, par.default
	return d

def listing():
	return {
		'type': 'list',
		'project': project.name.replace('.toe', ''),
		'patches': [{'op': o.name, 'label': o.name.replace('_', ' '), 'count': len(controls_page(o).pars)} for o in comps()],
	}

def state(o):
	return {'type': 'state', 'op': o.name, 'controls': [describe(p) for p in controls_page(o).pars]}

# Paired phones, by connection id.
def paired():
	return me_comp().fetch('orrery_paired', set(), storeDefault=True)

def send(server, client, msg):
	server.webSocketSendText(client, json.dumps(msg))

def broadcast(msg):
	server = op('server')
	for client in list(paired()):
		send(server, client, msg)

def update_phones():
	me_comp().par.Phones = len(paired())

def address():
	# The LAN address other devices reach this machine on (no packet is sent).
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		s.connect(('10.255.255.255', 1))
		ip = s.getsockname()[0]
	except OSError:
		ip = '127.0.0.1'
	finally:
		s.close()
	port = int(me_comp().par.Port)
	return ip if port == 9980 else '%s:%d' % (ip, port)

def onWebSocketOpen(webServerDAT, client, uri):
	code = parse_qs(urlparse(uri).query).get('code', [''])[0]
	if code and hmac.compare_digest(code, me_comp().par.Code.eval()):
		paired().add(client)
		update_phones()
		return
	send(webServerDAT, client, {'type': 'denied'})
	close = getattr(webServerDAT, 'webSocketClose', None)
	if close:
		close(client)
	return

def onWebSocketClose(webServerDAT, client):
	paired().discard(client)
	update_phones()
	return

def onWebSocketReceiveText(webServerDAT, client, data):
	if client not in paired():
		send(webServerDAT, client, {'type': 'denied'})
		return
	try:
		msg = json.loads(data)
		kind = msg.get('type')
		if kind == 'list':
			reply = listing()
		else:
			o = find(msg.get('op'))
			if kind == 'set':
				par = next((p for p in controls_page(o).pars if p.name == msg.get('par')), None)
				if par is None or par.readOnly:
					raise ValueError('not a control: %s' % msg.get('par'))
				if par.style == 'Pulse':
					par.pulse()
				else:
					par.val = msg['value']
				return  # parexec sends the new state to every phone
			reply = state(o)
	except Exception as e:
		reply = {'type': 'error', 'error': str(e)}
	send(webServerDAT, client, reply)
	return

def onHTTPRequest(webServerDAT, request, response):
	response['statusCode'] = 200
	response['statusReason'] = 'OK'
	response['data'] = 'Orrery is running. Open the Orrery app and pair with the code shown in TouchDesigner.'
	return response

def onWebSocketReceiveBinary(webServerDAT, client, data):
	return

def onWebSocketReceivePing(webServerDAT, client, data):
	webServerDAT.webSocketSendPong(client, data=data)
	return

def onWebSocketReceivePong(webServerDAT, client, data):
	return

def onServerStart(webServerDAT):
	paired().clear()
	update_phones()
	return

def onServerStop(webServerDAT):
	paired().clear()
	update_phones()
	return
