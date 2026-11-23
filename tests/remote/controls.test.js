// Every kind of control on a panel, rendered from tests/fixtures/synth_state.json (the same
// fixture the Python tests check orrery_callbacks.describe() against).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { load, STATE, clone } from './harness.js';

const IDX = Object.fromEntries(STATE.controls.map((c, i) => [c.name, i]));

function panel(state = STATE) {
  const r = load({ stored: '123456' });
  const s = r.openPanel(state);
  const node = (name) => r.$('.card').children[IDX[name] + 1];
  const push = (changes) => {
    const st = clone(state);
    for (const c of st.controls) if (c.name in changes) c.value = changes[c.name];
    s.receive(st);
  };
  return { r, s, node, push };
}

function withControls(controls) {
  return panel({ type: 'state', op: 'synth', controls });
}

test('one node per control, in order, under the patch title', () => {
  const { r } = panel();
  const card = r.$('.card');
  assert.equal(card.children[0].tagName, 'H1');
  assert.equal(card.children.length, STATE.controls.length + 1);
});

// --- Header --------------------------------------------------------------------------------

test('a Header becomes an upper-case group title', () => {
  const { node } = panel();
  assert.equal(node('Tone').className, 'group');
  assert.equal(node('Tone').textContent, 'TONE');
});

// --- Float ---------------------------------------------------------------------------------

test('a Float is a slider across its range', () => {
  const { node } = panel();
  const range = node('Cutoff').querySelector('input[type=range]');
  assert.equal(range.min, '0');
  assert.equal(range.max, '1');
  assert.equal(range.step, '0.001');
  assert.equal(+range.value, 0.25);
  assert.equal(range.getAttribute('aria-label'), 'Cutoff');
});

test('small ranges show two decimals, wide ranges one', () => {
  const { node } = panel();
  assert.equal(node('Cutoff').querySelector('.val').textContent, '0.25');
  assert.equal(node('Gain').querySelector('.val').textContent, '12.0');
});

test('a Float without a range defaults to 0..1', () => {
  const { r } = withControls([{ name: 'X', label: 'X', style: 'Float', value: 0.5 }]);
  const range = r.$('input[type=range]');
  assert.equal(range.min, '0');
  assert.equal(range.max, '1');
});

test('a zero-width range still gets a usable step', () => {
  const { r } = withControls([{ name: 'X', label: 'X', style: 'Float', value: 1, min: 1, max: 1, default: 1 }]);
  assert.equal(r.$('input[type=range]').step, '0.001');
});

test('moving the slider sends the value at once', () => {
  const { r, s, node } = panel();
  const range = node('Cutoff').querySelector('input');
  r.type(range, '0.6');
  assert.deepEqual(s.take(), [{ type: 'set', op: 'synth', par: 'Cutoff', value: 0.6 }]);
  assert.equal(node('Cutoff').querySelector('.val').textContent, '0.60');
});

test('while moving, it sends at most every 50 ms and always the latest value', () => {
  const { r, s, node } = panel();
  const range = node('Cutoff').querySelector('input');
  r.type(range, '0.1');
  r.advance(10); r.type(range, '0.2');
  r.advance(10); r.type(range, '0.3');
  assert.deepEqual(s.take().map((m) => m.value), [0.1]);
  r.advance(49);
  assert.deepEqual(s.take(), []);
  r.advance(1);
  assert.deepEqual(s.take().map((m) => m.value), [0.3]);
});

test('a slow drag sends every move', () => {
  const { r, s, node } = panel();
  const range = node('Cutoff').querySelector('input');
  for (const v of ['0.1', '0.2', '0.3']) { r.type(range, v); r.advance(60); }
  assert.deepEqual(s.take().map((m) => m.value), [0.1, 0.2, 0.3]);
});

test('letting go sends the final value once and cancels the pending one', () => {
  const { r, s, node } = panel();
  const range = node('Cutoff').querySelector('input');
  r.type(range, '0.1');
  r.advance(10); r.type(range, '0.4');
  r.fire(range, 'change');
  r.advance(1000);
  assert.deepEqual(s.take().map((m) => m.value), [0.1, 0.4]);
});

test('updates from TouchDesigner do not move a slider under a finger', () => {
  const { r, node, push } = panel();
  const range = node('Cutoff').querySelector('input');
  r.type(range, '0.7');
  push({ Cutoff: 0.1 });
  assert.equal(+range.value, 0.7);
  assert.equal(node('Cutoff').querySelector('.val').textContent, '0.70');
  r.fire(range, 'change');
  push({ Cutoff: 0.1 });
  assert.equal(+range.value, 0.1);
  assert.equal(node('Cutoff').querySelector('.val').textContent, '0.10');
});

test('updates from TouchDesigner move an idle slider', () => {
  const { node, push } = panel();
  push({ Gain: -6 });
  assert.equal(+node('Gain').querySelector('input').value, -6);
  assert.equal(node('Gain').querySelector('.val').textContent, '-6.0');
});

// --- Reset ---------------------------------------------------------------------------------

test('Reset shows only when a value is off its default', () => {
  const { node, push } = panel();
  const reset = (n) => node(n).querySelector('.reset');
  assert.equal(reset('Cutoff').hidden, false); // 0.25 vs 0.5
  assert.equal(reset('Voices').hidden, true);  // 4 vs 4
  push({ Cutoff: 0.5, Voices: 6 });
  assert.equal(reset('Cutoff').hidden, true);
  assert.equal(reset('Voices').hidden, false);
});

test('Reset sends the default', () => {
  const { s, node } = panel();
  node('Gain').querySelector('.reset').click();
  assert.deepEqual(s.take(), [{ type: 'set', op: 'synth', par: 'Gain', value: 0 }]);
});

test('no default, no Reset', () => {
  const { r } = withControls([{ name: 'X', label: 'X', style: 'Float', value: 0.3, min: 0, max: 1 }]);
  assert.equal(r.$('.reset').hidden, true);
});

test('Reset appears while dragging off the default', () => {
  const { r, node } = panel();
  r.fire(node('Cutoff').querySelector('.reset'), 'click');
  const range = node('Cutoff').querySelector('input');
  r.type(range, '0.5');
  assert.equal(node('Cutoff').querySelector('.reset').hidden, true);
  r.type(range, '0.9');
  assert.equal(node('Cutoff').querySelector('.reset').hidden, false);
});

// --- Int -----------------------------------------------------------------------------------

test('an Int is a − / + stepper', () => {
  const { r, node } = panel();
  assert.equal(node('Voices').querySelector('.step .val').textContent, '4');
  assert.ok(r.button('Voices down'));
  assert.ok(r.button('Voices up'));
});

test('+ and − send the new value', () => {
  const { r, s, node } = panel();
  r.button('Voices up').click();
  r.button('Voices up').click();
  r.button('Voices down').click();
  assert.deepEqual(s.take().map((m) => m.value), [5, 6, 5]);
  assert.equal(node('Voices').querySelector('.step .val').textContent, '5');
});

test('the stepper stops at the range', () => {
  const { r, s } = panel();
  for (let i = 0; i < 10; i++) r.button('Voices up').click();
  assert.equal(s.take().at(-1).value, 8);
  for (let i = 0; i < 10; i++) r.button('Voices down').click();
  assert.equal(s.take().at(-1).value, 1);
});

test('the stepper follows TouchDesigner', () => {
  const { r, s, node, push } = panel();
  push({ Voices: 7 });
  assert.equal(node('Voices').querySelector('.step .val').textContent, '7');
  r.button('Voices up').click();
  assert.equal(s.take()[0].value, 8);
});

test('Int values are shown without decimals', () => {
  const { node, push } = panel();
  push({ Voices: 3 });
  assert.equal(node('Voices').querySelector('.step .val').textContent, '3');
});

// --- Toggle --------------------------------------------------------------------------------

test('a Toggle is a switch that flips', () => {
  const { s, node } = panel();
  const sw = node('Bypass').querySelector('.switch');
  assert.equal(sw.getAttribute('role'), 'switch');
  assert.equal(sw.getAttribute('aria-label'), 'Bypass');
  assert.equal(sw.getAttribute('aria-checked'), 'false');
  sw.click();
  assert.equal(sw.getAttribute('aria-checked'), 'true');
  sw.click();
  assert.deepEqual(s.take().map((m) => m.value), [true, false]);
});

test('the switch follows TouchDesigner', () => {
  const { s, node, push } = panel();
  const sw = node('Bypass').querySelector('.switch');
  push({ Bypass: true });
  assert.equal(sw.getAttribute('aria-checked'), 'true');
  sw.click();
  assert.equal(s.take()[0].value, false);
});

test('a Toggle reported as 1/0 still works', () => {
  const { r } = withControls([{ name: 'T', label: 'T', style: 'Toggle', value: 1 }]);
  assert.equal(r.$('.switch').getAttribute('aria-checked'), 'true');
});

// --- Menu ----------------------------------------------------------------------------------

test('a Menu is a row of choices with the current one pressed', () => {
  const { node } = panel();
  const btns = [...node('Wave').querySelectorAll('.segs button')];
  assert.deepEqual(btns.map((b) => b.textContent), ['Sine', 'Saw', 'Square']);
  assert.deepEqual(btns.map((b) => b.getAttribute('aria-pressed')), ['false', 'true', 'false']);
});

test('choosing sends the menu name, not the label', () => {
  const { s, node } = panel();
  node('Wave').querySelectorAll('.segs button')[2].click();
  assert.deepEqual(s.take(), [{ type: 'set', op: 'synth', par: 'Wave', value: 'square' }]);
});

test('the pressed choice follows TouchDesigner', () => {
  const { node, push } = panel();
  push({ Wave: 'sine' });
  const pressed = [...node('Wave').querySelectorAll('.segs button')].map((b) => b.getAttribute('aria-pressed'));
  assert.deepEqual(pressed, ['true', 'false', 'false']);
});

test('a String Menu works the same way', () => {
  const { r, s } = withControls([{ name: 'Clip', label: 'Clip', style: 'StrMenu', value: 'b', options: [['a', 'A'], ['b', 'B']] }]);
  const btns = r.$$('.segs button');
  assert.equal(btns[1].getAttribute('aria-pressed'), 'true');
  btns[0].click();
  assert.deepEqual(s.take(), [{ type: 'set', op: 'synth', par: 'Clip', value: 'a' }]);
});

test('a Menu with no options renders empty, not broken', () => {
  const { r } = withControls([{ name: 'M', label: 'M', style: 'Menu', value: 'x' }]);
  assert.equal(r.$$('.segs button').length, 0);
});

// --- Pulse ---------------------------------------------------------------------------------

test('a Pulse is a tap button that sends no value', () => {
  const { s, node } = panel();
  const b = node('Trigger');
  assert.equal(b.tagName, 'BUTTON');
  assert.equal(b.textContent, 'Trigger');
  b.click();
  assert.deepEqual(s.take(), [{ type: 'set', op: 'synth', par: 'Trigger' }]);
});

test('a Pulse flashes for 150 ms', () => {
  const { r, node } = panel();
  const b = node('Trigger');
  b.click();
  assert.ok(b.classList.contains('down'));
  r.advance(149);
  assert.ok(b.classList.contains('down'));
  r.advance(1);
  assert.ok(!b.classList.contains('down'));
});

test('every tap is sent', () => {
  const { s, node } = panel();
  for (let i = 0; i < 5; i++) node('Trigger').click();
  assert.equal(s.take().length, 5);
});

// --- Momentary -----------------------------------------------------------------------------

test('a Momentary is held: true on press, false on release', () => {
  const { r, s, node } = panel();
  const b = node('Hold');
  assert.equal(b.textContent, 'Hold · hold');
  const e = r.fire(b, 'pointerdown');
  assert.equal(e.defaultPrevented, true);
  assert.ok(b.classList.contains('down'));
  r.fire(b, 'pointerup');
  assert.ok(!b.classList.contains('down'));
  assert.deepEqual(s.take().map((m) => m.value), [true, false]);
});

for (const ending of ['pointercancel', 'pointerleave']) {
  test(`a Momentary is released on ${ending}`, () => {
    const { r, s, node } = panel();
    r.fire(node('Hold'), 'pointerdown');
    r.fire(node('Hold'), ending);
    assert.deepEqual(s.take().map((m) => m.value), [true, false]);
  });
}

test('a second finger does not press twice, and release is sent once', () => {
  const { r, s, node } = panel();
  r.fire(node('Hold'), 'pointerdown');
  r.fire(node('Hold'), 'pointerdown');
  r.fire(node('Hold'), 'pointerup');
  r.fire(node('Hold'), 'pointerleave');
  assert.deepEqual(s.take().map((m) => m.value), [true, false]);
});

test('release without press sends nothing', () => {
  const { r, s, node } = panel();
  r.fire(node('Hold'), 'pointerup');
  r.fire(node('Hold'), 'pointerleave');
  assert.deepEqual(s.take(), []);
});

test('a long press does not open the context menu', () => {
  const { r, node } = panel();
  assert.equal(r.fire(node('Hold'), 'contextmenu').defaultPrevented, true);
});

// --- read-only and everything else ---------------------------------------------------------

test('a Str parameter is shown as its value, read only', () => {
  const { node } = panel();
  const row = node('Name');
  assert.equal(row.className, 'row');
  assert.equal(row.querySelector('.val').textContent, 'lead');
  assert.equal(row.querySelector('input, button'), null);
});

test('a read-only Float is shown, never a slider', () => {
  const { node } = panel();
  assert.equal(node('Level').querySelector('input'), null);
  assert.equal(node('Level').querySelector('.val').textContent, '0.8');
});

test('read-only values follow TouchDesigner', () => {
  const { node, push } = panel();
  push({ Level: 0.3, Name: 'bass' });
  assert.equal(node('Level').querySelector('.val').textContent, '0.3');
  assert.equal(node('Name').querySelector('.val').textContent, 'bass');
});

for (const style of ['Toggle', 'Menu', 'Pulse', 'Momentary', 'Int']) {
  test(`a read-only ${style} is shown, not controllable`, () => {
    const { r } = withControls([{ name: 'X', label: 'X', style, value: 1, readOnly: true, options: [['a', 'A']] }]);
    assert.equal(r.$('.card .row .val').textContent, '1');
    assert.equal(r.$$('.card button, .card input').length, 0);
  });
}

test('an unknown style with a non-number value is read only', () => {
  const { r } = withControls([{ name: 'R', label: 'Ref', style: 'OP', value: '/project1/geo' }]);
  assert.equal(r.text('.card .row .val'), '/project1/geo');
});

test('a missing value shows as empty', () => {
  const { r } = withControls([{ name: 'R', label: 'R', style: 'Str' }]);
  assert.equal(r.text('.card .row .val'), '');
});

test('an unknown style with a number value gets a slider', () => {
  // XY, RGB members etc. arrive one by one as numbers; they are treated like Floats.
  const { r } = withControls([{ name: 'Tx', label: 'Tx', style: 'XYZ', value: 0.5 }]);
  assert.ok(r.$('input[type=range]'));
});

// --- rebuilding ----------------------------------------------------------------------------

test('a state with the same controls updates in place', () => {
  const { r, push } = panel();
  const before = r.$$('.card > *');
  push({ Cutoff: 0.9, Bypass: true });
  const after = r.$$('.card > *');
  assert.equal(after.length, before.length);
  after.forEach((n, i) => assert.equal(n, before[i]));
});

test('a state with different controls rebuilds the panel', () => {
  const { r, s } = panel();
  const range = r.$('input[type=range]');
  const st = clone(STATE);
  st.controls.push({ name: 'New', label: 'New', style: 'Toggle', value: true });
  s.receive(st);
  assert.notEqual(r.$('input[type=range]'), range);
  assert.equal(r.$('.card').children.length, STATE.controls.length + 2);
});

test('a control changing style rebuilds the panel', () => {
  const { r, s } = panel();
  const st = clone(STATE);
  st.controls[IDX.Bypass] = { name: 'Bypass', label: 'Bypass', style: 'Pulse', section: false };
  s.receive(st);
  assert.equal(r.$('.switch'), null);
});

test('reopening a patch after back builds it fresh', () => {
  const { r, s } = panel();
  const range = r.$('input[type=range]');
  r.$('.back').click();
  r.$('.list button').click();
  s.receive(clone(STATE));
  assert.notEqual(r.$('input[type=range]'), range);
});

test('an empty panel is just its title', () => {
  const { r } = withControls([]);
  assert.equal(r.$('.card').children.length, 1);
});

test('controls send to the patch they belong to', () => {
  const r = load({ stored: '123456' });
  const s = r.live();
  r.$$('.list button')[1].click();
  s.receive({ type: 'state', op: 'my_fx', controls: [{ name: 'On', label: 'On', style: 'Toggle', value: false }] });
  s.take();
  r.$('.switch').click();
  assert.deepEqual(s.take(), [{ type: 'set', op: 'my_fx', par: 'On', value: true }]);
});
