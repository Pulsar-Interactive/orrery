# orrery_settings.py, orrery_start.py and orrery_parexec.py.
import re

import pytest
from conftest import add_synth
from tdfake import COMP


@pytest.fixture(autouse=True)
def lan(world, monkeypatch):
	monkeypatch.setattr(world.cb, 'address', lambda: 'http://192.168.1.20:%d' % int(world.orrery.par.Port))


# --- pairing codes -------------------------------------------------------------------------

def test_new_code_is_six_digits(world):
	for _ in range(200):
		world.settings.new_code(world.orrery)
		assert re.fullmatch(r'\d{6}', world.orrery.par.Code.eval())


def test_new_code_keeps_leading_zeros(world, monkeypatch):
	class R:
		def randrange(self, n):
			assert n == 1000000
			return 42
	monkeypatch.setattr(world.settings.random, 'SystemRandom', R)
	world.settings.new_code(world.orrery)
	assert world.orrery.par.Code.eval() == '000042'


def test_new_code_uses_system_random(world, monkeypatch):
	used = []
	real = world.settings.random.SystemRandom
	monkeypatch.setattr(world.settings.random, 'SystemRandom', lambda: used.append(1) or real())
	world.settings.new_code(world.orrery)
	assert used


def test_new_codes_vary(world):
	codes = set()
	for _ in range(50):
		world.settings.new_code(world.orrery)
		codes.add(world.orrery.par.Code.eval())
	assert len(codes) > 40


# --- refresh -------------------------------------------------------------------------------

def test_refresh_sets_address_and_watches_root(world):
	world.settings.refresh(world.orrery)
	assert world.orrery.par.Address.eval() == 'http://192.168.1.20:9980'
	assert world.parexec_dat.par.ops.eval() == '/project1/*'


def test_refresh_follows_root(world):
	rack = COMP('rack', world.project)
	world.orrery.par.Root = rack
	world.settings.refresh(world.orrery)
	assert world.parexec_dat.par.ops.eval() == '/project1/rack/*'


def test_refresh_uses_op_when_there_is_no_ops_parameter(world):
	# Older TouchDesigner builds call the Parameter Execute DAT's OPs parameter `op`.
	from tdfake import Par, ParCollection
	world.parexec_dat.par = ParCollection()
	world.parexec_dat.par.add(Par('op', 'Str', value=''))
	world.settings.refresh(world.orrery)
	assert world.parexec_dat.par.op.eval() == '/project1/*'


# --- parameter changes on the component ----------------------------------------------------

@pytest.mark.parametrize('name', ['Port', 'Root', 'Page'])
def test_port_root_page_refresh(world, name):
	world.orrery.par.Port = 9990
	world.settings.onValueChange(getattr(world.orrery.par, name), None)
	assert world.orrery.par.Address.eval() == 'http://192.168.1.20:9990'


@pytest.mark.parametrize('name', ['Root', 'Page', 'Onair'])
def test_root_and_page_rebroadcast_the_list(world, synth, name):
	world.pair('a')
	world.pair('b')
	world.settings.onValueChange(getattr(world.orrery.par, name), None)
	assert sorted((c, m['type']) for c, m in world.server.sent) == [('a', 'list'), ('b', 'list')]


def test_port_change_does_not_broadcast(world):
	world.pair('a')
	world.settings.onValueChange(world.orrery.par.Port, 9980)
	assert world.server.sent == []


@pytest.mark.parametrize('name', ['Active', 'Code', 'Phones', 'Address'])
def test_other_parameters_do_nothing(world, name):
	world.pair('a')
	world.settings.onValueChange(getattr(world.orrery.par, name), None)
	assert world.server.sent == [] and world.orrery.par.Address.eval() == ''


# --- pulses --------------------------------------------------------------------------------

def test_new_code_pulse_changes_code_and_restarts_server(world):
	world.settings.onPulse(world.orrery.par.Newcode)
	assert re.fullmatch(r'\d{6}', world.orrery.par.Code.eval())
	assert world.server.par.active.history == [False, True]


def test_new_code_pulse_drops_old_phones(world, monkeypatch):
	# Restarting the server fires onServerStop/onServerStart, which forget every phone.
	class R:
		def randrange(self, n):
			return 777777
	monkeypatch.setattr(world.settings.random, 'SystemRandom', R)
	world.pair('a')
	world.settings.onPulse(world.orrery.par.Newcode)
	world.cb.onServerStop(world.server)
	world.cb.onServerStart(world.server)
	assert world.cb.paired() == set()
	world.cb.onWebSocketOpen(world.server, 'a', '/?code=123456')
	assert 'a' not in world.cb.paired()
	world.cb.onWebSocketOpen(world.server, 'a', '/?code=777777')
	assert 'a' in world.cb.paired()


def test_refresh_pulse(world):
	world.settings.onPulse(world.orrery.par.Refresh)
	assert world.orrery.par.Address.eval() == 'http://192.168.1.20:9980'


def test_unknown_pulse_does_nothing(world):
	world.settings.onPulse(world.orrery.par.Active)
	assert world.orrery.par.Code.eval() == '123456'
	assert world.server.par.active.history == []


# --- Show QR -------------------------------------------------------------------------------
# The QR is drawn inside the component (Script TOP `qrtop`) and opened in a viewer window: no
# browser, no file, no internet.

def test_show_qr_opens_the_qr_viewer(world):
	world.settings.onPulse(world.orrery.par.Showqr)
	assert world.qrtop.viewers == 1
	assert world.qrtop.cooks >= 1


def test_show_qr_refreshes_first(world):
	world.orrery.par.Port = 10000
	world.settings.show_qr(world.orrery)
	assert world.orrery.par.Address.eval() == 'http://192.168.1.20:10000'


def test_show_qr_draws_the_address_with_the_code(world, monkeypatch):
	drawn = []
	real = world.qr.matrix
	monkeypatch.setattr(world.qr, 'matrix', lambda text, mask=None: drawn.append(text) or real(text, mask))
	world.settings.show_qr(world.orrery)
	world.draw_qr()
	assert drawn[-1] == 'http://192.168.1.20:9980/?code=123456'


def test_show_qr_sends_nothing_to_phones(world):
	world.pair('a')
	world.settings.show_qr(world.orrery)
	assert world.server.sent == []


def test_new_code_redraws_the_qr(world):
	before = getattr(world.qrtop, 'cooks', 0)
	world.settings.new_code(world.orrery)
	assert world.qrtop.cooks == before + 1


def test_refresh_redraws_the_qr(world):
	before = getattr(world.qrtop, 'cooks', 0)
	world.settings.refresh(world.orrery)
	assert world.qrtop.cooks == before + 1


# --- start ---------------------------------------------------------------------------------

def test_start_makes_a_code_when_there_is_none(world):
	world.orrery.par.Code = ''
	world.start.onStart()
	assert re.fullmatch(r'\d{6}', world.orrery.par.Code.eval())
	assert world.orrery.par.Address.eval() == 'http://192.168.1.20:9980'


def test_start_keeps_an_existing_code(world):
	world.start.onStart()
	assert world.orrery.par.Code.eval() == '123456'


def test_create_runs_start(world):
	world.orrery.par.Code = ''
	world.start.onCreate()
	assert world.orrery.par.Code.eval() != ''
	assert world.parexec_dat.par.ops.eval() == '/project1/*'


# --- parexec: pushing TouchDesigner changes to the phones ----------------------------------

def test_control_change_is_pushed_to_every_phone(world, synth):
	world.pair('a')
	world.pair('b')
	synth.par.Cutoff = 0.7
	world.parexec.onValueChange(synth.par.Cutoff, 0.25)
	assert sorted(c for c, _ in world.server.sent) == ['a', 'b']
	state = world.server.sent[0][1]
	assert state['type'] == 'state' and state['op'] == 'synth'
	assert next(c for c in state['controls'] if c['name'] == 'Cutoff')['value'] == 0.7


def test_phone_set_round_trips_through_parexec(world, synth):
	# The phone's set sends nothing itself; TouchDesigner then fires parexec, which pushes state.
	a, b = world.pair('a'), world.pair('b')
	assert world.ask(a, {'type': 'set', 'op': 'synth', 'par': 'Voices', 'value': 6}) == []
	world.parexec.onValueChange(synth.par.Voices, 4)
	for c in (a, b):
		[msg] = world.server.to(c)
		assert next(x for x in msg['controls'] if x['name'] == 'Voices')['value'] == 6


def test_change_on_another_page_is_not_pushed(world, synth):
	world.pair('a')
	p = synth.page('Private').add('Secret', 'Float', value=0)
	world.parexec.onValueChange(p, 1)
	assert world.server.sent == []


def test_change_on_comp_without_controls_page_is_not_pushed(world):
	world.pair('a')
	c = world.comp('plain', page=None)
	p = c.page('Other').add('X', 'Float')
	world.parexec.onValueChange(p, 0)
	assert world.server.sent == []


def test_change_on_a_builtin_parameter_is_not_pushed(world, synth):
	# Built-in parameters have no custom page.
	world.pair('a')
	from tdfake import Par
	world.parexec.onValueChange(Par('tx', owner=synth, page=None), 0)
	assert world.server.sent == []


def test_change_on_the_orrery_component_is_not_pushed(world):
	world.pair('a')
	p = world.orrery.page('Controls').add('X', 'Float')
	world.parexec.onValueChange(p, 0)
	assert world.server.sent == []


def test_change_follows_the_page_parameter(world):
	world.pair('a')
	c = world.comp('rig', page='Setup')
	p = c.page('Setup').add('X', 'Float', value=1)
	world.orrery.par.Page = 'Setup'
	world.parexec.onValueChange(p, 0)
	assert [m['op'] for _, m in world.server.sent] == ['rig']


def test_change_with_no_phones_sends_nothing(world, synth):
	world.parexec.onValueChange(synth.par.Cutoff, 0)
	assert world.server.sent == []


def test_parexec_pulse_is_ignored(world, synth):
	world.pair('a')
	world.parexec.onPulse(synth.par.Trigger)
	assert world.server.sent == []


def test_many_comps_push_only_their_own_state(world):
	world.pair('a')
	add_synth(world, 'one')
	two = add_synth(world, 'two')
	world.parexec.onValueChange(two.par.Gain, 0)
	assert [m['op'] for _, m in world.server.sent] == ['two']


def test_control_change_that_moves_on_air_also_pushes_the_list(world, synth):
	world.pair('a')
	world.ask('a', {'type': 'list'})  # a phone asks for the list when it connects
	world.server.sent.clear()
	world.orrery.par.Onair = 'synth'
	world.parexec.onValueChange(synth.par.Cutoff, 0.25)
	assert [m['type'] for m in world.server.to('a')] == ['state', 'list']
	assert world.server.to('a')[1]['live'] == 'synth'


def test_list_is_pushed_only_when_on_air_changes(world, synth):
	world.pair('a')
	world.ask('a', {'type': 'list'})  # a phone asks for the list when it connects
	world.server.sent.clear()
	world.orrery.par.Onair = 'synth'
	world.parexec.onValueChange(synth.par.Cutoff, 0.25)
	world.parexec.onValueChange(synth.par.Cutoff, 0.5)
	assert [m['type'] for m in world.server.to('a')] == ['state', 'list', 'state']


# --- the Setup page ------------------------------------------------------------------------

SETUP = ('Okserver', 'Okcomps', 'Okpage', 'Okphone')


def ticks(world):
	return {n: bool(getattr(world.orrery.par, n).eval()) for n in SETUP}


def test_setup_with_nothing_beside_orrery(world):
	world.settings.check_setup(world.orrery)
	assert ticks(world) == {'Okserver': True, 'Okcomps': False, 'Okpage': False, 'Okphone': False}
	assert world.orrery.par.Nextstep.eval().startswith('Put a COMP next to Orrery')


def test_setup_a_comp_without_the_page(world):
	COMP('plain', world.project)
	world.settings.check_setup(world.orrery)
	assert ticks(world) == {'Okserver': True, 'Okcomps': True, 'Okpage': False, 'Okphone': False}
	assert 'named Controls' in world.orrery.par.Nextstep.eval()


def test_setup_follows_the_page_name(world):
	add_synth(world)
	world.orrery.par.Page = 'Other'
	world.settings.check_setup(world.orrery)
	assert ticks(world)['Okpage'] is False
	assert 'named Other' in world.orrery.par.Nextstep.eval()


def test_setup_a_hidden_comp_does_not_count(world):
	add_synth(world).tags.add('orrery-hide')
	world.settings.check_setup(world.orrery)
	assert ticks(world)['Okpage'] is False


def test_setup_a_controls_page_asks_for_a_phone(world):
	add_synth(world)
	world.settings.check_setup(world.orrery)
	assert ticks(world) == {'Okserver': True, 'Okcomps': True, 'Okpage': True, 'Okphone': False}
	assert world.orrery.par.Nextstep.eval() == 'Press Show QR and scan it with a phone.'


def test_setup_all_set_with_a_phone(world):
	add_synth(world)
	world.orrery.par.Phones = 1
	world.settings.check_setup(world.orrery)
	assert all(ticks(world).values())
	assert world.orrery.par.Nextstep.eval().startswith('Everything is set')


def test_setup_server_off(world):
	world.server.par.active.val = False
	world.settings.check_setup(world.orrery)
	assert ticks(world)['Okserver'] is False
	assert world.orrery.par.Nextstep.eval().startswith('Turn Active on')


def test_setup_follows_changes(world):
	world.settings.check_setup(world.orrery)
	assert ticks(world)['Okpage'] is False
	add_synth(world)
	world.settings.check_setup(world.orrery)
	assert ticks(world)['Okpage'] is True


def test_setup_writes_only_what_changed(world):
	add_synth(world)
	world.settings.check_setup(world.orrery)
	written = {n: list(getattr(world.orrery.par, n).history) for n in SETUP + ('Nextstep', 'Guide')}
	world.settings.check_setup(world.orrery)  # nothing changed, so nothing is written
	assert written == {n: list(getattr(world.orrery.par, n).history) for n in SETUP + ('Nextstep', 'Guide')}


def test_setup_names_the_guide(world):
	world.settings.check_setup(world.orrery)
	assert world.orrery.par.Guide.eval() == 'https://orrery.pulsarinteractive.ai/#how'


def test_refresh_checks_setup(world):
	world.settings.refresh(world.orrery)
	assert world.orrery.par.Nextstep.eval()


def test_check_setup_pulse(world):
	world.settings.onPulse(world.orrery.par.Checksetup)
	assert world.orrery.par.Nextstep.eval()


def test_help_pulse_opens_the_guide(world):
	world.settings.onPulse(world.orrery.par.Help)
	assert world.viewed == ['https://orrery.pulsarinteractive.ai/#how']


def test_start_frame_end_rechecks_once_a_second(world):
	for frame in (1, 59, 61):
		world.start.onFrameEnd(frame)
	assert world.orrery.par.Nextstep.eval() == ''  # not a multiple of 60: nothing ran
	world.start.onFrameEnd(60)
	assert world.orrery.par.Nextstep.eval()
