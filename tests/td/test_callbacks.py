# orrery_callbacks.py: discovery, describing parameters, pairing, the WebSocket protocol, HTTP.
import json

import pytest
from conftest import FIXTURES, add_synth
from tdfake import COMP, DAT


# --- discovery -----------------------------------------------------------------------------

def test_lists_only_comps_with_a_controls_page(world, synth):
	world.comp('fx')
	world.comp('no_page', page=None)
	world.comp('other_page', page='Setup')
	DAT('notes', world.project)
	assert [o.name for o in world.cb.comps()] == ['synth', 'fx']


def test_never_lists_itself(world):
	world.orrery.page('Controls').add('Sneaky', 'Float', value=0)
	assert world.cb.comps() == []


def test_page_name_follows_the_page_parameter(world, synth):
	world.comp('setup_only', page='Setup')
	world.orrery.par.Page = 'Setup'
	assert [o.name for o in world.cb.comps()] == ['setup_only']


def test_empty_page_name_falls_back_to_controls(world, synth):
	world.orrery.par.Page = ''
	assert world.cb.page_name() == 'Controls'
	assert [o.name for o in world.cb.comps()] == ['synth']


def test_root_defaults_to_the_components_parent(world):
	assert world.cb.root() is world.project


def test_root_parameter_moves_discovery(world, synth):
	rack = COMP('rack', world.project)
	add_synth(world, 'inner', parent=rack)
	world.orrery.par.Root = rack
	assert [o.name for o in world.cb.comps()] == ['inner']


def test_nested_comps_are_not_listed(world, synth):
	add_synth(world, 'deep', parent=synth)
	assert [o.name for o in world.cb.comps()] == ['synth']


def test_page_match_is_case_sensitive(world):
	world.comp('lower', page='controls')
	assert world.cb.comps() == []


# --- find: the only way a phone names an operator ------------------------------------------

def test_find_returns_a_controllable_comp(world, synth):
	assert world.cb.find('synth') is synth


@pytest.mark.parametrize('name', ['missing', '', None, 'orrery', 'server', 'callbacks', 'synth/deep',
	'/project1/synth/deep', '../project1', '..', '.', '/', '/project1'])
def test_find_rejects_anything_else(world, synth, name):
	add_synth(world, 'deep', parent=synth)
	with pytest.raises(ValueError, match='nothing to control'):
		world.cb.find(name)


@pytest.mark.parametrize('name', ['/project1/synth', '../project1/synth', './synth'])
def test_find_paths_that_land_on_an_allowed_comp_are_that_comp(world, synth, name):
	# Harmless: a path is only accepted when it resolves to a COMP directly under Root with the page.
	assert world.cb.find(name) is synth


def test_find_rejects_a_comp_without_the_page(world):
	world.comp('plain', page=None)
	with pytest.raises(ValueError):
		world.cb.find('plain')


def test_find_rejects_comps_outside_root(world, synth):
	rack = COMP('rack', world.project)
	world.orrery.par.Root = rack
	with pytest.raises(ValueError):
		world.cb.find('synth')


# --- describe ------------------------------------------------------------------------------

def test_describe_matches_the_shared_fixture(world, synth):
	# fixtures/synth_state.json is also what the remote's tests render, so the two sides agree.
	expected = json.loads((FIXTURES / 'synth_state.json').read_text())
	assert world.cb.state(synth) == expected


def test_describe_float(world, synth):
	d = world.cb.describe(synth.par.Gain)
	assert d == {'name': 'Gain', 'label': 'Gain', 'style': 'Float', 'section': False,
		'value': 12.0, 'min': -24.0, 'max': 24.0, 'default': 0.0}


def test_describe_header_has_no_value(world, synth):
	d = world.cb.describe(synth.par.Tone)
	assert d['style'] == 'Header' and d['section'] is True
	assert 'value' not in d


@pytest.mark.parametrize('style', ['Pulse', 'Momentary', 'Header'])
def test_describe_skips_value_for_actions(world, style):
	c = world.comp('c')
	p = c.page('Controls').add('X', style, value=True)
	assert 'value' not in world.cb.describe(p)


def test_describe_menu_options(world, synth):
	assert world.cb.describe(synth.par.Wave)['options'] == [['sine', 'Sine'], ['saw', 'Saw'], ['square', 'Square']]


def test_describe_str_menu_options(world):
	c = world.comp('c')
	p = c.page('Controls').add('Clip', 'StrMenu', value='b', menuNames=['a', 'b'], menuLabels=['A', 'B'])
	d = world.cb.describe(p)
	assert d['options'] == [['a', 'A'], ['b', 'B']] and d['value'] == 'b'


def test_describe_read_only(world, synth):
	d = world.cb.describe(synth.par.Level)
	assert d['readOnly'] is True


def test_describe_writable_has_no_read_only_key(world, synth):
	assert 'readOnly' not in world.cb.describe(synth.par.Cutoff)


@pytest.mark.parametrize('value', [True, 3, 0.5, 'text'])
def test_describe_keeps_json_values(world, value):
	p = world.comp('c').page('Controls').add('V', 'Str', value=value)
	assert world.cb.describe(p)['value'] == value


@pytest.mark.parametrize('value, expected', [(None, 'None'), ((1, 2), '(1, 2)'), (COMP('someop'), '<COMP /someop>')])
def test_describe_stringifies_other_values(world, value, expected):
	# OP references, tuples, None... anything json.dumps might choke on becomes a string.
	p = world.comp('c').page('Controls').add('V', 'OP', value=value)
	d = world.cb.describe(p)
	assert d['value'] == expected
	json.dumps(d)


def test_state_is_json_serialisable(world, synth):
	json.dumps(world.cb.state(synth))


# --- listing -------------------------------------------------------------------------------

def test_listing(world, synth):
	world.comp('my_fx').page('Controls').add('Mix', 'Float', value=0)
	assert world.cb.listing() == {'type': 'list', 'project': 'show', 'live': '', 'recording': None, 'patches': [
		{'op': 'my_fx', 'label': 'my fx', 'count': 1, 'canLive': False, 'show': False},
		{'op': 'synth', 'label': 'synth', 'count': 10, 'canLive': False, 'show': False},
	]}


def test_listing_is_sorted_by_label_ignoring_case(world):
	for name in ('Zeta', 'alpha', 'Mid_way'):
		world.comp(name)
	assert [p['op'] for p in world.cb.listing()['patches']] == ['alpha', 'Mid_way', 'Zeta']


def test_listing_live_is_the_on_air_value(world, synth):
	world.orrery.par.Onair = 'synth'
	assert world.cb.listing()['live'] == 'synth'


def test_hidden_comp_is_left_out_of_the_list(world, synth):
	world.comp('secret').tags.add('orrery-hide')
	assert [p['op'] for p in world.cb.listing()['patches']] == ['synth']


def test_hidden_comp_cannot_be_read_or_changed(world):
	c = world.comp('secret')
	c.page('Controls').add('Mix', 'Float', value=0.5)
	c.tags.add('orrery-hide')
	phone = world.pair()
	nope = [{'type': 'error', 'error': 'nothing to control called secret'}]
	assert world.ask(phone, {'type': 'get', 'op': 'secret'}) == nope
	assert world.ask(phone, {'type': 'set', 'op': 'secret', 'par': 'Mix', 'value': 1}) == nope
	assert c.par.Mix.eval() == 0.5


def test_listing_when_nothing_to_control(world):
	assert world.cb.listing()['patches'] == []


@pytest.mark.parametrize('toe, name', [('show.toe', 'show'), ('festival.42.toe', 'festival'),
		('my.show.toe', 'my.show'), ('v2.1.toe', 'v2')])
def test_listing_project_name_drops_toe_and_save_number(toe, name):
	from tdfake import World
	assert World(toe).cb.listing()['project'] == name


# --- pairing -------------------------------------------------------------------------------

def test_right_code_pairs(world):
	world.pair('a')
	assert 'a' in world.cb.paired()
	assert world.orrery.par.Phones.eval() == 1
	assert world.server.sent == [] and world.server.closed == []


@pytest.mark.parametrize('uri', ['/?code=000000', '/', '/?code=', '/?other=123456', '/?code=1234567',
	'/?code=12345', '/?code=%20123456'])
def test_wrong_code_is_denied_and_closed(world, uri):
	world.cb.onWebSocketOpen(world.server, 'x', uri)
	assert world.server.sent == [('x', {'type': 'denied'})]
	assert world.server.closed == ['x']
	assert 'x' not in world.cb.paired()
	assert world.orrery.par.Phones.eval() == 0


def test_empty_component_code_pairs_nobody(world):
	world.orrery.par.Code = ''
	world.cb.onWebSocketOpen(world.server, 'x', '/?code=')
	assert 'x' not in world.cb.paired()


def test_denied_without_close_support(world):
	# Older builds have no webSocketClose: still denied, just not closed.
	world.server.webSocketClose = None
	world.cb.onWebSocketOpen(world.server, 'x', '/?code=999999')
	assert world.server.sent == [('x', {'type': 'denied'})]


def test_code_compared_with_hmac(world, monkeypatch):
	calls = []
	real = world.cb.hmac.compare_digest
	monkeypatch.setattr(world.cb.hmac, 'compare_digest', lambda a, b: calls.append((a, b)) or real(a, b))
	world.pair('a')
	assert calls == [('123456', '123456')]


def test_extra_query_parameters_are_ignored(world):
	world.cb.onWebSocketOpen(world.server, 'a', '/?foo=1&code=123456&bar=2')
	assert 'a' in world.cb.paired()


def test_close_unpairs(world):
	world.pair('a')
	world.pair('b')
	world.cb.onWebSocketClose(world.server, 'a')
	assert world.cb.paired() == {'b'}
	assert world.orrery.par.Phones.eval() == 1


def test_close_of_unknown_client_is_harmless(world):
	world.cb.onWebSocketClose(world.server, 'ghost')
	assert world.orrery.par.Phones.eval() == 0


def test_server_start_and_stop_forget_phones(world):
	world.pair('a')
	world.cb.onServerStop(world.server)
	assert world.cb.paired() == set() and world.orrery.par.Phones.eval() == 0
	world.pair('b')
	world.cb.onServerStart(world.server)
	assert world.cb.paired() == set() and world.orrery.par.Phones.eval() == 0


def test_paired_set_lives_in_component_storage(world):
	world.pair('a')
	assert world.orrery.storage['orrery_paired'] == {'a'}


# --- messages ------------------------------------------------------------------------------

def test_unpaired_client_gets_denied_and_nothing_else(world, synth):
	for msg in ({'type': 'list'}, {'type': 'get', 'op': 'synth'}, {'type': 'set', 'op': 'synth', 'par': 'Cutoff', 'value': 1}):
		assert world.ask('stranger', msg) == [{'type': 'denied'}]
	assert synth.par.Cutoff.eval() == 0.25


def test_list(world, synth):
	c = world.pair()
	assert world.ask(c, {'type': 'list'}) == [world.cb.listing()]


def test_get(world, synth):
	c = world.pair()
	assert world.ask(c, {'type': 'get', 'op': 'synth'}) == [world.cb.state(synth)]


def test_get_unknown(world):
	c = world.pair()
	assert world.ask(c, {'type': 'get', 'op': 'nope'}) == [{'type': 'error', 'error': 'nothing to control called nope'}]


def test_get_without_op(world):
	c = world.pair()
	[reply] = world.ask(c, {'type': 'get'})
	assert reply['type'] == 'error' and reply['error'].startswith('nothing to control')


def test_unknown_type_is_treated_as_get(world, synth):
	# Anything that is not list or set answers with the state (or an error), never changes a value.
	c = world.pair()
	assert world.ask(c, {'type': 'whatever', 'op': 'synth'}) == [world.cb.state(synth)]


@pytest.mark.parametrize('par, value', [('Cutoff', 0.9), ('Voices', 7), ('Bypass', True), ('Wave', 'square'),
	('Name', 'bass'), ('Hold', True)])
def test_set_changes_the_value_and_sends_nothing(world, synth, par, value):
	c = world.pair()
	assert world.ask(c, {'type': 'set', 'op': 'synth', 'par': par, 'value': value}) == []
	assert getattr(synth.par, par).eval() == value


def test_set_pulse_pulses_and_ignores_value(world, synth):
	c = world.pair()
	world.ask(c, {'type': 'set', 'op': 'synth', 'par': 'Trigger'})
	world.ask(c, {'type': 'set', 'op': 'synth', 'par': 'Trigger', 'value': 'ignored'})
	assert synth.par.Trigger.pulses == 2
	assert synth.par.Trigger.history == []


def test_set_read_only_is_refused(world, synth):
	c = world.pair()
	assert world.ask(c, {'type': 'set', 'op': 'synth', 'par': 'Level', 'value': 0}) == [
		{'type': 'error', 'error': 'not a control: Level'}]
	assert synth.par.Level.eval() == 0.8


def test_set_parameter_not_on_the_page_is_refused(world, synth):
	# A real parameter of the COMP, but not on its Controls page.
	synth.page('Private').add('Secret', 'Float', value=1)
	c = world.pair()
	[reply] = world.ask(c, {'type': 'set', 'op': 'synth', 'par': 'Secret', 'value': 0})
	assert reply == {'type': 'error', 'error': 'not a control: Secret'}
	assert synth.par.Secret.eval() == 1


def test_set_on_another_page_name_is_refused(world, synth):
	world.orrery.par.Page = 'Setup'
	c = world.pair()
	[reply] = world.ask(c, {'type': 'set', 'op': 'synth', 'par': 'Cutoff', 'value': 1})
	assert reply['type'] == 'error'
	assert synth.par.Cutoff.eval() == 0.25


def test_set_on_the_component_itself_is_refused(world):
	c = world.pair()
	[reply] = world.ask(c, {'type': 'set', 'op': 'orrery', 'par': 'Code', 'value': '000000'})
	assert reply['type'] == 'error'
	assert world.orrery.par.Code.eval() == '123456'


def test_set_unknown_parameter_is_refused(world, synth):
	c = world.pair()
	assert world.ask(c, {'type': 'set', 'op': 'synth', 'par': 'Nope', 'value': 1}) == [
		{'type': 'error', 'error': 'not a control: Nope'}]


def test_set_without_value_is_an_error(world, synth):
	c = world.pair()
	[reply] = world.ask(c, {'type': 'set', 'op': 'synth', 'par': 'Cutoff'})
	assert reply['type'] == 'error'
	assert synth.par.Cutoff.eval() == 0.25


def test_set_value_rejected_by_td_becomes_an_error(world, synth):
	class Picky(type(synth.par.Cutoff)):
		def __setattr__(self, k, v):
			if k == 'val' and 'history' in self.__dict__ and isinstance(v, str):
				raise TypeError('bad value')
			super().__setattr__(k, v)
	synth.par.Cutoff.__class__ = Picky
	c = world.pair()
	assert world.ask(c, {'type': 'set', 'op': 'synth', 'par': 'Cutoff', 'value': 'loud'}) == [
		{'type': 'error', 'error': 'bad value'}]


@pytest.mark.parametrize('data', ['not json', '', '[]', '"list"', '42', 'null', '{"type": "list"'])
def test_garbage_is_an_error_not_a_crash(world, data):
	c = world.pair()
	world.cb.onWebSocketReceiveText(world.server, c, data)
	[(client, reply)] = world.server.sent
	assert client == c and reply['type'] == 'error'


def test_replies_go_only_to_the_sender(world, synth):
	a, b = world.pair('a'), world.pair('b')
	world.ask(a, {'type': 'list'})
	assert [client for client, _ in world.server.sent] == ['a']
	assert b in world.cb.paired()


def test_broadcast_reaches_every_paired_phone(world):
	world.pair('a')
	world.pair('b')
	world.cb.broadcast({'type': 'x'})
	assert sorted(c for c, _ in world.server.sent) == ['a', 'b']


def test_broadcast_with_no_phones(world):
	world.cb.broadcast({'type': 'x'})
	assert world.server.sent == []


def test_binary_and_pong_are_ignored(world):
	c = world.pair()
	world.cb.onWebSocketReceiveBinary(world.server, c, b'\x00')
	world.cb.onWebSocketReceivePong(world.server, c, b'')
	assert world.server.sent == []


def test_ping_gets_pong(world):
	world.cb.onWebSocketReceivePing(world.server, 'a', b'hi')
	assert world.server.pongs == [('a', b'hi')]


# --- HTTP ----------------------------------------------------------------------------------

@pytest.mark.parametrize('uri', ['/', '/index.html', '/?code=123456', '/index.html?x=1'])
def test_serves_the_remote(world, uri):
	r = world.cb.onHTTPRequest(world.server, {'method': 'GET', 'uri': uri}, {})
	assert r['statusCode'] == 200
	assert r['Content-Type'] == 'text/html; charset=utf-8'
	assert r['Cache-Control'] == 'no-store'
	assert r['data'] == world.remote.text
	assert '<title>Orrery</title>' in r['data']


def test_request_without_method_or_uri_defaults_to_get_root(world):
	assert world.cb.onHTTPRequest(world.server, {}, {})['statusCode'] == 200


@pytest.mark.parametrize('uri', ['/pair.html', '/orrery_callbacks.py', '/../td/build.py', '/favicon.ico',
	'/index.htm', '//', '/remote'])
def test_everything_else_is_404(world, uri):
	r = world.cb.onHTTPRequest(world.server, {'method': 'GET', 'uri': uri}, {})
	assert r['statusCode'] == 404 and r['data'] == 'Not found'


@pytest.mark.parametrize('method', ['POST', 'PUT', 'DELETE', 'HEAD'])
def test_only_get(world, method):
	assert world.cb.onHTTPRequest(world.server, {'method': method, 'uri': '/'}, {})['statusCode'] == 404


def test_pair_page_is_never_served(world):
	# The QR page holds the code; it must stay a local file.
	for uri in ('/', '/index.html'):
		assert '{{CODE}}' not in world.cb.onHTTPRequest(world.server, {'uri': uri}, {})['data']


def test_served_page_does_not_contain_the_code(world):
	r = world.cb.onHTTPRequest(world.server, {'uri': '/'}, {})
	assert world.orrery.par.Code.eval() not in r['data']


# --- address -------------------------------------------------------------------------------

class FakeSocket:
	def __init__(self, ip=None, fail=False):
		self.ip, self.fail, self.closed, self.connected = ip, fail, False, None

	def connect(self, addr):
		if self.fail:
			raise OSError('no network')
		self.connected = addr

	def getsockname(self):
		return (self.ip, 50000)

	def close(self):
		self.closed = True


def test_address_uses_lan_ip_and_port(world, monkeypatch):
	s = FakeSocket('192.168.1.20')
	monkeypatch.setattr(world.cb.socket, 'socket', lambda *a: s)
	world.orrery.par.Port = 9990
	assert world.cb.address() == 'http://192.168.1.20:9990'
	assert s.closed and s.connected == ('10.255.255.255', 1)


def test_address_falls_back_to_localhost(world, monkeypatch):
	s = FakeSocket(fail=True)
	monkeypatch.setattr(world.cb.socket, 'socket', lambda *a: s)
	assert world.cb.address() == 'http://127.0.0.1:9980'
	assert s.closed


def test_address_casts_port_to_int(world, monkeypatch):
	monkeypatch.setattr(world.cb.socket, 'socket', lambda *a: FakeSocket('10.0.0.2'))
	world.orrery.par.Port = 9981.0
	assert world.cb.address() == 'http://10.0.0.2:9981'
