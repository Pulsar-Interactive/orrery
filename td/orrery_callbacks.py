# Orrery: control TouchDesigner from a phone.
# Callbacks DAT of the Web Server DAT `server` inside the Orrery component.
#
# Every COMP next to the component (its Root parameter) that has a custom parameter page named
# like the component's Page parameter (default "Controls") shows up in the app, and every
# parameter on that page becomes a control. Nothing else in the project can be read or changed.
#
# The phone opens http://ADDRESS:PORT/ (the `remote` page), which connects to
# ws://ADDRESS:PORT/?code=CODE. A wrong code gets {"type": "denied"} and is
# closed; nothing is sent to or accepted from it.
#
# Messages (JSON):
#   -> {"type": "list"}                       <- {"type": "list", "project", "live", "recording", "patches": [{"op", "label", "count", "canLive"}]}
#   -> {"type": "get", "op": "synth"}         <- {"type": "state", "op", "controls": [...]}
#   -> {"type": "set", "op", "par", "value"}  (Pulse parameters ignore value)
#   -> {"type": "live", "op": "synth"}        puts it on air (sets the parameter On Air names); every phone gets a new list
#   -> {"type": "record", "on": true}         starts or stops recording (the toggle Record names); every phone gets a new list
#   <- {"type": "error", "error": "..."}
# `parexec` pushes a fresh "state" to every paired phone when a control changes in TouchDesigner.
import base64
import hmac
import json
import re
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
	# A COMP tagged orrery-hide keeps its Controls page (for other tools) but stays off the phone.
	return [o for o in root().children if controls_page(o) and 'orrery-hide' not in o.tags]

def find(name):
	o = root().op(str(name))
	if o is None or o.parent() != root() or o not in comps():
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

def label(o):
	# The COMP's name as words: my_patch -> my patch
	return o.name.replace('_', ' ')

def project_name():
	# myshow.12.toe -> myshow (TouchDesigner's save number is not part of the name)
	return re.sub(r'(\.\d+)?\.toe$', '', project.name)

def live():
	return me_comp().par.Onair.eval() if hasattr(me_comp().par, 'Onair') else ''

def named_par(name, style=None):
	# A component parameter set to an expression naming a parameter, e.g. op('show').par.Patch.
	p = getattr(me_comp().par, name, None)
	if p is None or p.mode != ParMode.EXPRESSION:
		return None
	try:
		t = me_comp().evalExpression(p.expr)
	except Exception:
		return None
	return t if isinstance(t, td.Par) and not t.readOnly and style in (None, t.style) else None

def live_par():
	# On Air: the phone's Go Live sets it.
	return named_par('Onair')

def record_par():
	# Record, e.g. op('recorder').par.Record: the phone's REC button flips it.
	return named_par('Record', 'Toggle')

def recording():
	p = record_par()
	return bool(p.eval()) if p is not None else None

def can_go_live(par, name):
	return par is not None and (not par.isMenu or name in par.menuNames)

def check_live():
	# Every phone gets a fresh list when what's on air, or recording, changed.
	now = '%s|%s' % (live(), recording())
	if now != me_comp().fetch('orrery_live', '', storeDefault=True):
		me_comp().store('orrery_live', now)
		broadcast(listing())

def listing():
	items = sorted(comps(), key=lambda o: label(o).lower())
	lp = live_par()
	return {
		'type': 'list',
		'project': project_name(),
		'live': live(),
		'recording': recording(),
		'patches': [{'op': o.name, 'label': label(o), 'count': len(controls_page(o).pars), 'canLive': can_go_live(lp, o.name)} for o in items],
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
	return 'http://%s:%d' % (ip, int(me_comp().par.Port))

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
		elif kind == 'live':
			name, lp = find(msg.get('op')).name, live_par()
			if not can_go_live(lp, name):
				raise ValueError('%s can not go live from here' % name)
			lp.val = name
			check_live()
			return
		elif kind == 'record':
			rp = record_par()
			if rp is None:
				raise ValueError('no recorder set on the Orrery component')
			rp.val = bool(msg.get('on'))
			check_live()
			return
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

TYPES = {'webmanifest': 'application/manifest+json', 'svg': 'image/svg+xml', 'png': 'image/png'}

def onHTTPRequest(webServerDAT, request, response):
	# The phone remote is a single page (the `remote` DAT). It holds no secrets: the pairing code
	# is checked when it opens the WebSocket.
	path = urlparse(request.get('uri', '/')).path
	if request.get('method', 'GET') == 'GET' and path in ('/', '/index.html'):
		response['statusCode'] = 200
		response['statusReason'] = 'OK'
		response['Content-Type'] = 'text/html; charset=utf-8'
		response['Cache-Control'] = 'no-store'
		response['data'] = op('remote').text
	elif request.get('method', 'GET') == 'GET' and op('assets')[path.lstrip('/'), 1] is not None:
		# The app manifest, its icons and the Pulsar logo (td/web, base64 in the `assets` table).
		response['statusCode'] = 200
		response['statusReason'] = 'OK'
		response['Content-Type'] = TYPES[path.rsplit('.', 1)[-1]]
		response['Cache-Control'] = 'max-age=86400'
		response['data'] = base64.b64decode(op('assets')[path.lstrip('/'), 1].val)
	else:
		response['statusCode'] = 404
		response['statusReason'] = 'Not Found'
		response['data'] = 'Not found'
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
