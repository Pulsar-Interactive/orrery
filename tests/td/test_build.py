# build.py: the component it builds, checked against the scripts and the README.
import re
import types

import pytest
from tdfake import COMP, DAT, TD_DIR, ScriptTOP, TableDAT, WebServer

README = (TD_DIR.parent / 'README.md').read_text(encoding='utf-8')
TD_README = (TD_DIR / 'README.md').read_text(encoding='utf-8')


class BuildCOMP(COMP):
	def __init__(self, name, parent=None):
		super().__init__(name, parent)
		self.unstored = []
		self.saved = []

	def create(self, kind, name):
		return kind(name, self)

	def unstore(self, pattern):
		self.unstored.append(pattern)
		self.storage.clear()

	def save(self, path):
		# what is saved is what a new project gets: snapshot the parameters that matter
		self.saved.append((path, self.par.Code.eval()))


class StartDAT(DAT):
	def __init__(self, name, parent=None):
		super().__init__(name, parent)
		self.calls = []
		owner = self
		self.module = types.SimpleNamespace(onStart=lambda: owner.calls.append(('onStart', len(owner._parent.saved))))


class ServerDAT(WebServer):
	pass


class BuildScriptTOP(ScriptTOP):
	def __init__(self, name, parent=None):
		super().__init__(name, parent)
		# the default callbacks DAT TouchDesigner docks to a new Script TOP
		self.docked = [DAT(name + '_callbacks_default', parent)]


@pytest.fixture
def built(capsys):
	top = BuildCOMP('')
	home = BuildCOMP('project1', top)
	old = BuildCOMP('orrery', home)
	g = {
		'op': lambda path: top.op(path),
		'baseCOMP': BuildCOMP, 'textDAT': DAT, 'webserverDAT': ServerDAT, 'tableDAT': TableDAT, 'scriptTOP': BuildScriptTOP,
		'parameterexecuteDAT': DAT, 'executeDAT': StartDAT,
		'TD_DIR': str(TD_DIR), '__name__': '__build__',
	}
	exec(compile((TD_DIR / 'build.py').read_text(encoding='utf-8'), str(TD_DIR / 'build.py'), 'exec'), g)
	comp = home.op('orrery')
	return types.SimpleNamespace(home=home, old=old, comp=comp, out=capsys.readouterr().out)


def page_pars(built):
	[page] = built.comp.customPages
	return page, {p.name: p for p in page.pars}


def test_replaces_an_existing_component(built):
	assert built.comp is not built.old
	assert [c.name for c in built.home.children] == ['orrery']
	assert built.old.parent() is None


def test_component_basics(built):
	assert built.comp.color == (0.31, 0.83, 0.87)
	assert 'Orrery' in built.comp.comment


def test_one_page_called_orrery(built):
	page, _ = page_pars(built)
	assert page.name == 'Orrery'


def test_parameters_in_order(built):
	page, _ = page_pars(built)
	assert [(p.name, p.style, p.label) for p in page.pars] == [
		('Active', 'Toggle', 'Active'),
		('Showqr', 'Pulse', 'Show QR'),
		('Address', 'Str', 'Address'),
		('Code', 'Str', 'Pairing Code'),
		('Newcode', 'Pulse', 'New Pairing Code'),
		('Phones', 'Int', 'Phones Connected'),
		('Port', 'Int', 'Port'),
		('Root', 'COMP', 'Controls In'),
		('Page', 'Str', 'Page Name'),
		('Onair', 'Str', 'On Air'),
		('Record', 'Str', 'Record'),
		('Refresh', 'Pulse', 'Refresh Address'),
	]


def test_read_only_parameters(built):
	_, pars = page_pars(built)
	assert {n for n, p in pars.items() if p.readOnly} == {'Address', 'Code', 'Phones'}


def test_defaults_are_applied(built):
	_, pars = page_pars(built)
	assert pars['Active'].eval() is True
	assert pars['Port'].eval() == 9980
	assert pars['Root'].eval() == '..'
	assert pars['Page'].eval() == 'Controls'


def test_port_range(built):
	_, pars = page_pars(built)
	p = pars['Port']
	assert (p.normMin, p.normMax, p.min, p.clampMin) == (1024, 65535, 1024, True)


def test_dats_hold_the_files(built):
	for name, filename in (('callbacks', 'orrery_callbacks.py'), ('remote', 'remote.html'), ('qr', 'orrery_qr.py'),
			('qrtop_callbacks', 'orrery_qrtop.py'), ('parexec', 'orrery_parexec.py'), ('settings', 'orrery_settings.py'),
			('start', 'orrery_start.py')):
		assert built.comp.op(name).text == (TD_DIR / filename).read_text(encoding='utf-8'), name


def test_operators_match_the_td_readme(built):
	documented = re.findall(r'^\| `(\w+)` \|', TD_README, re.M)
	assert sorted(documented) == sorted(c.name for c in built.comp.children)


def test_assets_hold_every_web_file_as_base64(built):
	import base64
	table = built.comp.op('assets')
	files = sorted(f for f in (TD_DIR / 'web').iterdir() if not f.name.startswith('.'))
	assert table.numRows == len(files)
	for f in files:
		assert base64.b64decode(table[f.name, 1].val) == f.read_bytes(), f.name


def test_qr_top_draws_with_our_callbacks_only(built):
	qt = built.comp.op('qrtop')
	assert isinstance(qt, BuildScriptTOP)
	assert qt.par.callbacks.eval() is built.comp.op('qrtop_callbacks')
	# TouchDesigner's default callbacks DAT is removed, so only orrery_qrtop.py runs
	assert not any(c.name.endswith('_callbacks_default') for c in built.comp.children)


def test_server_follows_the_component(built):
	s = built.comp.op('server')
	assert isinstance(s, ServerDAT)
	assert s.par.callbacks.eval() == 'callbacks'
	assert s.par.port.expr == 'parent().par.Port'
	assert s.par.active.expr == 'parent().par.Active'


def test_parexec_watches_values_not_pulses(built):
	pe = built.comp.op('parexec')
	assert pe.par.pars.eval() == '*'
	assert pe.par.valuechange.eval() is True
	assert pe.par.onpulse.eval() is False


def test_settings_watches_the_component(built):
	st = built.comp.op('settings')
	assert st.par.ops.eval() == '..'
	assert st.par.valuechange.eval() is True and st.par.onpulse.eval() is True
	watched = st.par.pars.eval().split()
	_, pars = page_pars(built)
	assert set(watched) <= set(pars)
	assert set(watched) == {'Port', 'Root', 'Page', 'Onair', 'Record', 'Newcode', 'Refresh', 'Showqr'}


def test_every_pulse_is_handled_by_settings(built):
	_, pars = page_pars(built)
	settings_src = (TD_DIR / 'orrery_settings.py').read_text()
	watched = built.comp.op('settings').par.pars.eval().split()
	for name, p in pars.items():
		if p.style == 'Pulse':
			assert name in watched and "'%s'" % name in settings_src, name


def test_start_runs_on_start_and_create(built):
	ex = built.comp.op('start')
	assert ex.par.start.eval() is True and ex.par.create.eval() is True


def test_saved_without_a_code_then_started(built):
	[(path, code)] = built.comp.saved
	assert path == str(TD_DIR / 'orrery.tox')
	assert code == ''
	assert built.comp.unstored == ['*']
	# onStart runs only after saving, so the code it makes stays out of the .tox
	assert built.comp.op('start').calls == [('onStart', 1)]


def test_prints_where_it_saved(built):
	assert 'Orrery built and saved to %s' % (TD_DIR / 'orrery.tox') in built.out


def test_nodes_do_not_overlap(built):
	spots = [(c.nodeX, c.nodeY) for c in built.comp.children]
	assert len(spots) == len(set(spots))


# --- docs stay in step with the build ------------------------------------------------------

def test_readme_settings_table_matches_the_parameters(built):
	section = README.split('## Settings', 1)[1].split('\n## ', 1)[0]
	documented = re.findall(r'^\| ([^|]+?) \|', section, re.M)
	documented = [d for d in documented if d not in ('Parameter',) and not set(d) <= set('-')]
	page, _ = page_pars(built)
	assert documented == [p.label for p in page.pars]


def test_readme_port_default(built):
	assert re.search(r'^\| Port \| 9980 \|', README, re.M)


def test_readme_lists_every_style_the_remote_handles():
	table = README.split('## What becomes what', 1)[1].split('\n## ', 1)[0]
	for style in ('Float', 'Int', 'Toggle', 'Momentary', 'Pulse', 'Menu', 'String Menu', 'Header', 'Read-only'):
		assert style in table, style


def test_protocol_comment_and_td_readme_agree():
	cb = (TD_DIR / 'orrery_callbacks.py').read_text()
	messages = re.findall(r'(->|<-) (\{.*?\})', TD_README)
	assert messages
	for arrow, msg in messages:
		assert '%s %s' % (arrow, msg) in cb, msg
