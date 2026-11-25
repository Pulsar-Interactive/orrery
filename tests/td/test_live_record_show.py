# GO LIVE and REC (the component's On Air and Record expressions), the SHOW section
# (orrery-show) and the files the component serves besides the remote (td/web).
import base64

import pytest
from conftest import add_synth
from tdfake import TD_DIR


@pytest.fixture
def show(world):
	"""A show-control COMP with a Patch menu (what is on air) and a Record toggle."""
	s = world.comp('show_ctl', page=None)
	pg = s.page('Settings')
	pg.add('Patch', 'Menu', value='synth', menuNames=['synth', 'my_fx'], menuLabels=['Synth', 'My FX'])
	pg.add('Record', 'Toggle', value=False)
	return s


@pytest.fixture
def two(world, synth):
	world.comp('my_fx').page('Controls').add('Mix', 'Float', value=0)
	world.comp('other').page('Controls').add('X', 'Float', value=0)
	return synth


def on_air(world, expr="op('show_ctl').par.Patch"):
	world.orrery.par.Onair.express(expr)


def recorder(world, expr="op('show_ctl').par.Record"):
	world.orrery.par.Record.express(expr)


def patches(world):
	return {p['op']: p for p in world.cb.listing()['patches']}


# --- GO LIVE ---------------------------------------------------------------------------------

def test_without_on_air_nothing_can_go_live(world, two):
	assert not any(p['canLive'] for p in patches(world).values())


def test_on_air_as_a_plain_value_is_shown_but_not_settable(world, two):
	world.orrery.par.Onair = 'synth'
	assert world.cb.listing()['live'] == 'synth'
	assert not any(p['canLive'] for p in patches(world).values())


def test_on_air_menu_lets_its_entries_go_live(world, two, show):
	on_air(world)
	p = patches(world)
	assert p['synth']['canLive'] and p['my_fx']['canLive']
	assert not p['other']['canLive']  # not one of the menu's entries
	assert world.cb.listing()['live'] == 'synth'


def test_on_air_string_parameter_lets_anything_go_live(world, two, show):
	show.page('Settings').add('Current', 'Str', value='')
	on_air(world, "op('show_ctl').par.Current")
	assert all(p['canLive'] for p in patches(world).values())


def test_go_live_sets_on_air_and_every_phone_gets_the_list(world, two, show):
	on_air(world)
	a, b = world.pair('a'), world.pair('b')
	assert world.ask(a, {'type': 'live', 'op': 'my_fx'}) == [{**world.cb.listing()}]
	assert show.par.Patch.eval() == 'my_fx'
	assert world.server.to(b)[-1]['live'] == 'my_fx'


def test_go_live_with_a_patch_not_in_the_menu_is_refused(world, two, show):
	on_air(world)
	a = world.pair('a')
	[err] = world.ask(a, {'type': 'live', 'op': 'other'})
	assert err == {'type': 'error', 'error': 'other can not go live from here'}
	assert show.par.Patch.eval() == 'synth'


def test_go_live_without_on_air_is_refused(world, two):
	a = world.pair('a')
	[err] = world.ask(a, {'type': 'live', 'op': 'synth'})
	assert err['type'] == 'error'


def test_go_live_with_a_hidden_comp_is_refused(world, two, show):
	on_air(world)
	world.project.op('my_fx').tags.add('orrery-hide')
	a = world.pair('a')
	[err] = world.ask(a, {'type': 'live', 'op': 'my_fx'})
	assert err == {'type': 'error', 'error': 'nothing to control called my_fx'}


def test_read_only_on_air_target_is_not_settable(world, two, show):
	show.par.Patch.readOnly = True
	on_air(world)
	assert not any(p['canLive'] for p in patches(world).values())


@pytest.mark.parametrize('expr', ["op('nowhere').par.Patch", 'syntax error (', "'just text'"])
def test_broken_or_non_parameter_on_air_is_ignored(world, two, show, expr):
	on_air(world, expr)
	assert world.cb.live_par() is None
	assert not any(p['canLive'] for p in patches(world).values())


# --- REC -------------------------------------------------------------------------------------

def test_without_a_recorder_recording_is_none(world, two):
	assert world.cb.listing()['recording'] is None


def test_recorder_state_is_in_the_list(world, two, show):
	recorder(world)
	assert world.cb.listing()['recording'] is False
	show.par.Record = True
	assert world.cb.listing()['recording'] is True


def test_record_starts_and_stops_and_every_phone_hears(world, two, show):
	recorder(world)
	a, b = world.pair('a'), world.pair('b')
	world.ask(a, {'type': 'record', 'on': True})
	assert show.par.Record.eval() is True
	assert world.server.to(b)[-1]['recording'] is True
	world.ask(b, {'type': 'record', 'on': False})
	assert show.par.Record.eval() is False
	assert world.server.to(a)[-1]['recording'] is False


def test_record_without_a_recorder_is_refused(world, two):
	a = world.pair('a')
	assert world.ask(a, {'type': 'record', 'on': True}) == [
		{'type': 'error', 'error': 'no recorder set on the Orrery component'}]


def test_recorder_must_be_a_toggle(world, two, show):
	recorder(world, "op('show_ctl').par.Patch")  # a menu, not a toggle
	assert world.cb.record_par() is None
	assert world.cb.listing()['recording'] is None


def test_record_message_is_coerced_to_a_bool(world, two, show):
	recorder(world)
	world.ask(world.pair('a'), {'type': 'record', 'on': 1})
	assert show.par.Record.eval() is True


def test_record_changes_on_air_fingerprint_once(world, two, show):
	# check_live sends a list only when what's on air or recording changes
	recorder(world)
	a = world.pair('a')
	world.ask(a, {'type': 'list'})
	world.server.sent.clear()
	world.parexec.onValueChange(two.par.Cutoff, 0)        # nothing moved: state only
	show.par.Record = True
	world.parexec.onValueChange(two.par.Cutoff, 0)        # recording started: state + list
	world.parexec.onValueChange(two.par.Cutoff, 0)        # nothing new: state only
	assert [m['type'] for m in world.server.to(a)] == ['state', 'state', 'list', 'state']


def test_on_air_moved_in_touchdesigner_reaches_phones_on_the_next_change(world, two, show):
	on_air(world)
	a = world.pair('a')
	world.ask(a, {'type': 'list'})
	world.server.sent.clear()
	show.par.Patch = 'my_fx'                              # changed on the laptop, not the phone
	world.parexec.onValueChange(two.par.Cutoff, 0)
	assert [m['type'] for m in world.server.to(a)] == ['state', 'list']
	assert world.server.to(a)[-1]['live'] == 'my_fx'


def test_first_control_change_sends_no_list(world, two):
	a = world.pair('a')
	world.parexec.onValueChange(two.par.Cutoff, 0)
	assert [m['type'] for m in world.server.to(a)] == ['state']


# --- SHOW section ----------------------------------------------------------------------------

def test_show_flag_follows_the_orrery_show_tag(world, two):
	world.project.op('my_fx').tags.add('orrery-show')
	p = patches(world)
	assert p['my_fx']['show'] is True
	assert p['synth']['show'] is False and p['other']['show'] is False


def test_hide_wins_over_show(world, two):
	c = world.project.op('my_fx')
	c.tags.update({'orrery-show', 'orrery-hide'})
	assert 'my_fx' not in patches(world)


def test_a_show_comp_is_controlled_like_any_other(world):
	sound = add_synth(world, 'sound')
	sound.tags.add('orrery-show')
	a = world.pair('a')
	world.ask(a, {'type': 'set', 'op': 'sound', 'par': 'Cutoff', 'value': 0.9})
	assert sound.par.Cutoff.eval() == 0.9


# --- served files (td/web) -------------------------------------------------------------------

WEB = sorted(f for f in (TD_DIR / 'web').iterdir() if not f.name.startswith('.'))
TYPES = {'.svg': 'image/svg+xml', '.png': 'image/png', '.webmanifest': 'application/manifest+json'}


@pytest.mark.parametrize('f', WEB, ids=lambda f: f.name)
def test_every_web_file_is_served_with_its_type(world, f):
	r = world.cb.onHTTPRequest(world.server, {'method': 'GET', 'uri': '/' + f.name}, {})
	assert r['statusCode'] == 200
	assert r['Content-Type'] == TYPES[f.suffix]
	assert r['data'] == f.read_bytes()
	assert 'max-age' in r['Cache-Control']


def test_web_files_ignore_the_query_string(world):
	r = world.cb.onHTTPRequest(world.server, {'method': 'GET', 'uri': '/icon.svg?v=2'}, {})
	assert r['statusCode'] == 200


def test_web_files_only_on_get(world):
	r = world.cb.onHTTPRequest(world.server, {'method': 'POST', 'uri': '/icon.svg'}, {})
	assert r['statusCode'] == 404


@pytest.mark.parametrize('uri', ['/../orrery_callbacks.py', '/web/icon.svg', '/assets', '/icon.SVG'])
def test_nothing_outside_the_table_is_served(world, uri):
	assert world.cb.onHTTPRequest(world.server, {'method': 'GET', 'uri': uri}, {})['statusCode'] == 404


def test_every_type_in_td_web_is_known():
	assert {f.suffix for f in WEB} <= set(TYPES)


def test_remote_links_only_files_that_are_served():
	html = (TD_DIR / 'remote.html').read_text(encoding='utf-8')
	import re
	linked = set(re.findall(r'(?:href|src)="/([\w.-]+)"', html))
	assert linked, 'expected the remote to load its icons and manifest'
	assert linked <= {f.name for f in WEB}


def test_assets_round_trip_base64(world):
	for f in WEB:
		assert base64.b64decode(world.assets[f.name, 1].val) == f.read_bytes()
