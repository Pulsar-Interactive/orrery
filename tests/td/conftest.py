import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from tdfake import World  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures'


@pytest.fixture
def world():
	return World()


def add_synth(world, name='synth', parent=None):
	"""A COMP with one of every parameter style Orrery knows, in the order of fixtures/synth_state.json."""
	c = world.comp(name, parent)
	pg = c.page('Controls')
	pg.add('Tone', 'Header', label='Tone', startSection=True)
	pg.add('Cutoff', 'Float', label='Cutoff', value=0.25, default=0.5, normMin=0.0, normMax=1.0)
	pg.add('Gain', 'Float', label='Gain', value=12.0, default=0.0, normMin=-24.0, normMax=24.0)
	pg.add('Voices', 'Int', label='Voices', value=4, default=4, normMin=1, normMax=8)
	pg.add('Bypass', 'Toggle', label='Bypass', value=False, default=False)
	pg.add('Wave', 'Menu', label='Wave', value='saw', menuNames=['sine', 'saw', 'square'],
		menuLabels=['Sine', 'Saw', 'Square'])
	pg.add('Trigger', 'Pulse', label='Trigger')
	pg.add('Hold', 'Momentary', label='Hold', value=False)
	pg.add('Name', 'Str', label='Name', value='lead')
	pg.add('Level', 'Float', label='Level', value=0.8, readOnly=True, normMin=0.0, normMax=1.0)
	return c


@pytest.fixture
def synth(world):
	return add_synth(world)
