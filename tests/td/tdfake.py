# A small fake of the parts of TouchDesigner the Orrery scripts use, so they can run under pytest.
# Only what td/*.py touches is modelled: COMPs with custom pages and parameters, DATs with a
# `module`, the Web Server DAT's send/close calls, `parent()`, `op()` and `project`.
import types
from pathlib import Path

TD_DIR = Path(__file__).resolve().parents[2] / 'td'


class Par:
	def __init__(self, name, style='Float', label=None, value=None, default=None, owner=None,
			page=None, readOnly=False, startSection=False, normMin=0.0, normMax=1.0,
			menuNames=(), menuLabels=()):
		self.name = name
		self.style = style
		self.label = label if label is not None else name
		self.val = value
		self.default = default
		self.owner = owner
		self.page = page
		self.readOnly = readOnly
		self.startSection = startSection
		self.normMin, self.normMax = normMin, normMax
		self.min, self.max = normMin, normMax
		self.clampMin = False
		self.menuNames, self.menuLabels = list(menuNames), list(menuLabels)
		self.expr = None
		self.pulses = 0
		self.history = []

	def eval(self):
		return self.val

	def pulse(self):
		self.pulses += 1

	# TD parameters cast like their value: int(comp.par.Port)
	def __int__(self):
		return int(self.val)

	def __float__(self):
		return float(self.val)

	def __setattr__(self, k, v):
		if k == 'val' and 'history' in self.__dict__:
			self.history.append(v)
		object.__setattr__(self, k, v)


class ParCollection:
	"""comp.par: attribute access returns a Par, assignment sets its value (like TD)."""

	def __init__(self, auto=False):
		object.__setattr__(self, '_pars', {})
		object.__setattr__(self, '_auto', auto)

	def add(self, par):
		self._pars[par.name] = par
		return par

	def __getattr__(self, k):
		pars = object.__getattribute__(self, '_pars')
		if k in pars:
			return pars[k]
		if object.__getattribute__(self, '_auto'):
			return self.add(Par(k, style='Str'))
		raise AttributeError(k)

	def __setattr__(self, k, v):
		getattr(self, k).val = v

	def __contains__(self, k):
		return k in self._pars


class Page:
	def __init__(self, name, owner):
		self.name = name
		self.owner = owner
		self.pars = []

	def add(self, name, style='Float', **kw):
		p = Par(name, style=style, owner=self.owner, page=self, **kw)
		self.pars.append(p)
		self.owner.par.add(p)
		return p

	# The appendX calls build.py uses; TD returns a ParGroup (a list).
	def _append(self, style, name, label=None, **kw):
		return [self.add(name, style=style, label=label or name, **kw)]

	def appendToggle(self, name, label=None):
		return self._append('Toggle', name, label, value=False, default=False)

	def appendPulse(self, name, label=None):
		return self._append('Pulse', name, label)

	def appendStr(self, name, label=None):
		return self._append('Str', name, label, value='', default='')

	def appendInt(self, name, label=None):
		return self._append('Int', name, label, value=0, default=0)

	def appendCOMP(self, name, label=None):
		return self._append('COMP', name, label, value=None, default='')


class OP:
	isCOMP = False

	def __init__(self, name, parent=None):
		self.name = name
		self._parent = parent
		self.par = ParCollection(auto=True)
		self.storage = {}
		self.children = []
		if parent is not None:
			parent.children.append(self)

	def parent(self):
		return self._parent

	@property
	def path(self):
		if self._parent is None:
			return '/' + self.name if self.name else '/'
		base = self._parent.path
		return (base.rstrip('/') + '/' + self.name)

	def op(self, path):
		path = str(path)
		if path.startswith('/'):
			node = self
			while node._parent is not None:
				node = node._parent
			parts = path.strip('/').split('/')
		else:
			node = self
			parts = path.split('/')
		for part in parts:
			if part in ('', '.'):
				continue
			if part == '..':
				node = node._parent
			else:
				node = next((c for c in node.children if c.name == part), None)
			if node is None:
				return None
		return node

	def fetch(self, key, default=None, storeDefault=False):
		if key not in self.storage:
			if storeDefault:
				self.storage[key] = default
			return default
		return self.storage[key]

	def destroy(self):
		if self._parent is not None:
			self._parent.children.remove(self)
			self._parent = None

	def __repr__(self):
		return '<%s %s>' % (type(self).__name__, self.path)


class COMP(OP):
	isCOMP = True

	def __init__(self, name, parent=None):
		super().__init__(name, parent)
		self.par = ParCollection()
		self.customPages = []

	def page(self, name):
		pg = next((p for p in self.customPages if p.name == name), None)
		if pg is None:
			pg = Page(name, self)
			self.customPages.append(pg)
		return pg

	appendCustomPage = page


class DAT(OP):
	def __init__(self, name, parent=None, text=''):
		super().__init__(name, parent)
		self.text = text
		self.module = None


class WebServer(DAT):
	def __init__(self, name='server', parent=None):
		super().__init__(name, parent)
		self.sent = []       # (client, decoded message)
		self.closed = []
		self.pongs = []
		self.par.active.val = True
		self.par.active.history = []

	def webSocketSendText(self, client, text):
		import json
		self.sent.append((client, json.loads(text)))

	def webSocketClose(self, client):
		self.closed.append(client)

	def webSocketSendPong(self, client, data=None):
		self.pongs.append((client, data))

	def to(self, client):
		import json  # noqa: F401
		return [m for c, m in self.sent if c == client]


def load_module(filename, me, project_name='show.toe', extra=None):
	"""Runs td/<filename> like a DAT inside `me` (the Orrery component) and returns its module."""
	mod = types.ModuleType(filename.replace('.py', ''))
	mod.__dict__.update({
		'parent': lambda: me,
		'op': lambda path: me.op(path),
		'project': types.SimpleNamespace(name=project_name),
	})
	if extra:
		mod.__dict__.update(extra)
	code = (TD_DIR / filename).read_text(encoding='utf-8')
	exec(compile(code, str(TD_DIR / filename), 'exec'), mod.__dict__)
	return mod


class World:
	"""/project1 with an Orrery component inside it, wired like build.py wires it."""

	def __init__(self, project_name='show.toe'):
		self.top = COMP('')
		self.project = COMP('project1', self.top)
		self.orrery = o = COMP('orrery', self.project)
		page = o.page('Orrery')
		page.add('Active', 'Toggle', value=True, default=True)
		page.add('Showqr', 'Pulse')
		page.add('Address', 'Str', value='', readOnly=True)
		page.add('Code', 'Str', value='', readOnly=True)
		page.add('Newcode', 'Pulse')
		page.add('Phones', 'Int', value=0, readOnly=True)
		page.add('Port', 'Int', value=9980, default=9980)
		page.add('Root', 'COMP', value=None)
		page.add('Page', 'Str', value='Controls', default='Controls')
		page.add('Refresh', 'Pulse')
		o.par.Code = '123456'

		self.server = WebServer('server', o)
		self.remote = DAT('remote', o, (TD_DIR / 'remote.html').read_text(encoding='utf-8'))
		self.pairpage = DAT('pairpage', o, (TD_DIR / 'pair.html').read_text(encoding='utf-8'))
		self.parexec_dat = DAT('parexec', o)
		self.parexec_dat.par.ops.val = ''
		for name, filename in (('callbacks', 'orrery_callbacks.py'), ('settings', 'orrery_settings.py'),
				('parexec', 'orrery_parexec.py'), ('start', 'orrery_start.py')):
			dat = o.op(name) or DAT(name, o)
			dat.module = load_module(filename, o, project_name)
		self.cb = o.op('callbacks').module
		self.settings = o.op('settings').module
		self.parexec = o.op('parexec').module
		self.start = o.op('start').module

	def comp(self, name, parent=None, page='Controls'):
		"""A COMP to control, with an (empty) custom page named `page`."""
		c = COMP(name, parent or self.project)
		if page:
			c.page(page)
		return c

	def pair(self, client='phone1', code=None):
		self.cb.onWebSocketOpen(self.server, client, '/?code=%s' % (code or self.orrery.par.Code.eval()))
		return client

	def ask(self, client, msg):
		import json
		before = len(self.server.sent)
		self.cb.onWebSocketReceiveText(self.server, client, json.dumps(msg))
		return [m for c, m in self.server.sent[before:] if c == client]
