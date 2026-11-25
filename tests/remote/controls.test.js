// Every kind of control on a panel, rendered from tests/fixtures/synth_state.json (the same
// fixture the Python tests check orrery_callbacks.describe() against).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { load, STATE, clone } from './harness.js';

const IDX = Object.fromEntries(STATE.controls.map((c, i) => [c.name, i]));

function panel(state = STATE) {
  const r = load({ stored: '123456' });
  const s = r.openPanel(state);
  // One entry per control, in order: buttons sharing a row (.btns) count one each.
  const nodes = () => [...r.$('.card').children]
    .flatMap((n) => n.classList.contains('btns') ? [...n.children] : [n]);
  const node = (name) => nodes()[IDX[name]];
  const push = (changes) => {
    const st = clone(state);
    for (const c of st.controls) if (c.name in changes) c.value = changes[c.name];
    s.receive(st);
  };
  // Values sent, rounded so float steps compare cleanly.
  const sent = () => s.take().map((m) => typeof m.value === 'number' ? +m.value.toFixed(4) : m.value);
  return { r, s, nodes, node, push, sent };
}

function withControls(controls) {
  return panel({ type: 'state', op: 'synth', controls });
}

const slider = (n) => n.querySelector('[role=slider]');
const shown = (n) => n.querySelector('.val').textContent;

test('one node per control, in order, under the patch title', () => {
  const { r, nodes } = panel();
  // the title sits above the card, with a way back to the list
  assert.equal(r.title(), 'synth');
  assert.ok(r.$('.title + .card'));
  assert.equal(r.$('.title .back').getAttribute('aria-label'), 'Back to the list');
  assert.equal(nodes().length, STATE.controls.length);
});

test('buttons next to each other share one row', () => {
  const { r, node } = panel();
  const rows = r.$$('.card > .btns');
  assert.equal(rows.length, 1);
  assert.deepEqual([...rows[0].children], [node('Trigger'), node('Hold')]);
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
  const sl = slider(node('Cutoff'));
  assert.equal(sl.getAttribute('aria-valuemin'), '0');
  assert.equal(sl.getAttribute('aria-valuemax'), '1');
  assert.equal(sl.getAttribute('aria-valuenow'), '0.25');
  assert.equal(sl.getAttribute('aria-label'), 'Cutoff');
  assert.equal(sl.getAttribute('tabindex'), '0');
});

test('decimals follow the range', () => {
  const { node } = panel();
  assert.equal(shown(node('Cutoff')), '0.25'); // range 1
  assert.equal(shown(node('Gain')), '12.0');   // range 48
  const { r } = withControls([
    { name: 'A', label: 'A', style: 'Float', value: 0.25, min: 0, max: 0.5 },
    { name: 'B', label: 'B', style: 'Float', value: 500, min: 0, max: 2000 },
  ]);
  assert.deepEqual(r.$$('.val').map((v) => v.textContent), ['0.250', '500']);
});

test('a Float without a range defaults to 0..1', () => {
  const { r } = withControls([{ name: 'X', label: 'X', style: 'Float', value: 0.5 }]);
  assert.equal(r.$('[role=slider]').getAttribute('aria-valuemin'), '0');
  assert.equal(r.$('[role=slider]').getAttribute('aria-valuemax'), '1');
});

test('a zero-width range does not break', () => {
  const { r, sent } = withControls([{ name: 'X', label: 'X', style: 'Float', value: 1, min: 1, max: 1, default: 1 }]);
  r.drag(r.$('[role=slider]'), 100).up();
  assert.deepEqual([...new Set(sent())], [1]);
});

test('dragging sideways moves by how far you drag and sends at once', () => {
  const { r, node, sent } = panel();
  r.drag(slider(node('Cutoff')), 105); // 105 px of a 300 px track: +0.35
  assert.deepEqual(sent(), [0.6]);
  assert.equal(shown(node('Cutoff')), '0.60');
});

test('a tap never changes the value', () => {
  const { r, node, sent } = panel();
  r.drag(slider(node('Cutoff')), 5).up(); // under 8 px is not a drag
  assert.deepEqual(sent(), []);
  assert.equal(shown(node('Cutoff')), '0.25');
});

test('a vertical swipe is a scroll, not a drag', () => {
  const { r, node, sent } = panel();
  const d = r.drag(slider(node('Cutoff')));
  d.to(10, 40);
  d.to(150);
  d.up();
  assert.deepEqual(sent(), []);
});

test('dragging stops at the ends of the range', () => {
  const { r, node, sent } = panel();
  r.drag(slider(node('Cutoff')), 1000).up();
  assert.deepEqual([...new Set(sent())], [1]);
  r.drag(slider(node('Cutoff')), -1000).up();
  assert.deepEqual([...new Set(sent())], [0]);
});

test('while moving, it sends at most every 50 ms and always the latest value', () => {
  const { r, node, sent } = panel();
  const d = r.drag(slider(node('Cutoff')), 30);
  r.advance(10); d.to(60);
  r.advance(10); d.to(90);
  assert.deepEqual(sent(), [0.35]);
  r.advance(49);
  assert.deepEqual(sent(), []);
  r.advance(1);
  assert.deepEqual(sent(), [0.55]);
});

test('a slow drag sends every move', () => {
  const { r, node, sent } = panel();
  const d = r.drag(slider(node('Cutoff')));
  for (const dx of [30, 60, 90]) { d.to(dx); r.advance(60); }
  assert.deepEqual(sent(), [0.35, 0.45, 0.55]);
});

test('letting go sends the final value once and cancels the pending one', () => {
  const { r, node, sent } = panel();
  const d = r.drag(slider(node('Cutoff')), 30);
  r.advance(10); d.to(60);
  d.up();
  r.advance(1000);
  assert.deepEqual(sent(), [0.35, 0.45]);
});

test('updates from TouchDesigner do not move a slider under a finger', () => {
  const { r, node, push } = panel();
  const d = r.drag(slider(node('Cutoff')), 135);
  push({ Cutoff: 0.1 });
  assert.equal(shown(node('Cutoff')), '0.70');
  d.up();
  push({ Cutoff: 0.1 });
  assert.equal(slider(node('Cutoff')).getAttribute('aria-valuenow'), '0.1');
  assert.equal(shown(node('Cutoff')), '0.10');
});

test('updates from TouchDesigner move an idle slider', () => {
  const { node, push } = panel();
  push({ Gain: -6 });
  assert.equal(slider(node('Gain')).getAttribute('aria-valuenow'), '-6');
  assert.equal(shown(node('Gain')), '-6.0');
});

test('arrow keys move the slider by a hundredth of its range', () => {
  const { r, node, sent } = panel();
  const key = (n, k) => slider(node(n)).dispatchEvent(new r.window.KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }));
  key('Cutoff', 'ArrowRight');
  assert.deepEqual([...new Set(sent())], [0.26]);
  key('Gain', 'ArrowDown');
  assert.deepEqual([...new Set(sent())], [11.52]);
  key('Gain', 'Enter');
  assert.deepEqual(sent(), []);
});

// --- Reset and Undo ------------------------------------------------------------------------

test('Reset stays hidden until you change the control, whatever TouchDesigner says', () => {
  const { node, push } = panel();
  const reset = (n) => node(n).querySelector('.reset');
  assert.equal(reset('Cutoff').hidden, true); // 0.25 is off its 0.5 default, but not your doing
  push({ Voices: 6 });
  assert.equal(reset('Voices').hidden, true);
});

test('moving a control off its default shows Reset', () => {
  const { r, node } = panel();
  r.button('Voices up').click();
  assert.equal(node('Voices').querySelector('.reset').hidden, false);
  r.button('Voices down').click();
  assert.equal(node('Voices').querySelector('.reset').hidden, true);
});

test('Reset appears while dragging off the default', () => {
  const { r, node } = panel();
  const d = r.drag(slider(node('Cutoff')), 75); // to 0.5, the default
  assert.equal(node('Cutoff').querySelector('.reset').hidden, true);
  d.to(195); // to 0.9
  assert.equal(node('Cutoff').querySelector('.reset').hidden, false);
});

test('Reset sends the default, and Undo puts the old value back', () => {
  const { r, node, sent } = panel();
  r.button('Voices up').click();
  sent();
  node('Voices').querySelector('.reset').click();
  assert.deepEqual(sent(), [4]);
  assert.equal(r.$('#toast').hidden, false);
  assert.equal(r.$('#toast span').textContent, 'Voices reset');
  r.button('Undo').click();
  assert.deepEqual(sent(), [5]);
  assert.equal(r.$('#toast').hidden, true);
});

test('the Undo message goes away after five seconds', () => {
  const { r, node } = panel();
  node('Gain').querySelector('.reset').click();
  r.advance(4999);
  assert.equal(r.$('#toast').hidden, false);
  r.advance(1);
  assert.equal(r.$('#toast').hidden, true);
});

test('no default, no Reset', () => {
  const { r } = withControls([{ name: 'X', label: 'X', style: 'Float', value: 0.3, min: 0, max: 1 }]);
  r.drag(r.$('[role=slider]'), 100).up();
  assert.equal(r.$('.reset').hidden, true);
});

// --- Int -----------------------------------------------------------------------------------

test('an Int is a − / + stepper', () => {
  const { r, node } = panel();
  assert.equal(node('Voices').querySelector('.step .val').textContent, '4');
  assert.ok(r.button('Voices down'));
  assert.ok(r.button('Voices up'));
});

test('+ and − send the new value', () => {
  const { r, node, sent } = panel();
  r.button('Voices up').click();
  r.button('Voices up').click();
  r.button('Voices down').click();
  assert.deepEqual(sent(), [5, 6, 5]);
  assert.equal(node('Voices').querySelector('.step .val').textContent, '5');
});

test('the stepper stops at the range and sends nothing past it', () => {
  const { r, sent } = panel();
  for (let i = 0; i < 10; i++) r.button('Voices up').click();
  assert.deepEqual(sent(), [5, 6, 7, 8]);
  for (let i = 0; i < 10; i++) r.button('Voices down').click();
  assert.deepEqual(sent(), [7, 6, 5, 4, 3, 2, 1]);
});

test('the stepper follows TouchDesigner', () => {
  const { r, node, push, sent } = panel();
  push({ Voices: 7 });
  assert.equal(node('Voices').querySelector('.step .val').textContent, '7');
  r.button('Voices up').click();
  assert.deepEqual(sent(), [8]);
});

test('Int values are shown without decimals', () => {
  const { node, push } = panel();
  push({ Voices: 3 });
  assert.equal(node('Voices').querySelector('.step .val').textContent, '3');
});

// --- Toggle --------------------------------------------------------------------------------

test('a Toggle is a whole-row switch that flips', () => {
  const { node, sent } = panel();
  const sw = node('Bypass');
  assert.equal(sw.tagName, 'BUTTON');
  assert.equal(sw.getAttribute('role'), 'switch');
  assert.equal(sw.firstChild.textContent, 'Bypass');
  assert.equal(sw.getAttribute('aria-checked'), 'false');
  sw.click();
  assert.equal(sw.getAttribute('aria-checked'), 'true');
  sw.click();
  assert.deepEqual(sent(), [true, false]);
});

test('the switch follows TouchDesigner', () => {
  const { node, push, sent } = panel();
  push({ Bypass: true });
  assert.equal(node('Bypass').getAttribute('aria-checked'), 'true');
  node('Bypass').click();
  assert.deepEqual(sent(), [false]);
});

test('a Toggle reported as 1/0 still works', () => {
  const { r } = withControls([{ name: 'T', label: 'T', style: 'Toggle', value: 1 }]);
  assert.equal(r.$('[role=switch]').getAttribute('aria-checked'), 'true');
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

test('choosing can be undone', () => {
  const { r, node, sent } = panel();
  node('Wave').querySelectorAll('.segs button')[2].click();
  assert.equal(r.$('#toast span').textContent, 'Wave: Square');
  sent();
  r.button('Undo').click();
  assert.deepEqual(sent(), ['saw']);
});

test('choosing the current choice sends nothing', () => {
  const { r, node, sent } = panel();
  node('Wave').querySelectorAll('.segs button')[1].click();
  assert.deepEqual(sent(), []);
  assert.equal(r.$('#toast').hidden, true);
});

test('the pressed choice follows TouchDesigner, and Undo goes back to it', () => {
  const { r, node, push, sent } = panel();
  push({ Wave: 'sine' });
  const pressed = [...node('Wave').querySelectorAll('.segs button')].map((b) => b.getAttribute('aria-pressed'));
  assert.deepEqual(pressed, ['true', 'false', 'false']);
  node('Wave').querySelectorAll('.segs button')[2].click();
  sent();
  r.button('Undo').click();
  assert.deepEqual(sent(), ['sine']);
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
  const { r, node, sent } = panel();
  const b = node('Hold');
  assert.equal(b.textContent, 'Hold (hold)');
  const e = r.fire(b, 'pointerdown');
  assert.equal(e.defaultPrevented, true);
  assert.ok(b.classList.contains('down'));
  r.fire(b, 'pointerup');
  assert.ok(!b.classList.contains('down'));
  assert.deepEqual(sent(), [true, false]);
});

for (const ending of ['pointercancel', 'pointerleave']) {
  test(`a Momentary is released on ${ending}`, () => {
    const { r, node, sent } = panel();
    r.fire(node('Hold'), 'pointerdown');
    r.fire(node('Hold'), ending);
    assert.deepEqual(sent(), [true, false]);
  });
}

test('a second finger does not press twice, and release is sent once', () => {
  const { r, node, sent } = panel();
  r.fire(node('Hold'), 'pointerdown');
  r.fire(node('Hold'), 'pointerdown');
  r.fire(node('Hold'), 'pointerup');
  r.fire(node('Hold'), 'pointerleave');
  assert.deepEqual(sent(), [true, false]);
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
  assert.equal(row.querySelector('.ro').textContent, 'lead');
  assert.equal(row.querySelector('input, button, [role=slider]'), null);
});

test('read-only names read as words; paths and file names stay as they are', () => {
  const { r } = withControls([
    { name: 'A', label: 'A', style: 'Str', value: 'my_clip_2' },
    { name: 'B', label: 'B', style: 'Str', value: '/project1/geo_1' },
    { name: 'C', label: 'C', style: 'Str', value: 'loop_v2.mov' },
  ]);
  assert.deepEqual(r.$$('.ro').map((v) => v.textContent), ['my clip 2', '/project1/geo_1', 'loop_v2.mov']);
});

test('a read-only Float is shown, never a slider', () => {
  const { node } = panel();
  assert.equal(slider(node('Level')), null);
  assert.equal(node('Level').querySelector('.ro').textContent, '0.8');
});

test('read-only values follow TouchDesigner', () => {
  const { node, push } = panel();
  push({ Level: 0.3, Name: 'bass' });
  assert.equal(node('Level').querySelector('.ro').textContent, '0.3');
  assert.equal(node('Name').querySelector('.ro').textContent, 'bass');
});

for (const style of ['Toggle', 'Menu', 'Pulse', 'Momentary', 'Int']) {
  test(`a read-only ${style} is shown, not controllable`, () => {
    const { r } = withControls([{ name: 'X', label: 'X', style, value: 1, readOnly: true, options: [['a', 'A']] }]);
    assert.equal(r.$('.card .row .ro').textContent, '1');
    assert.equal(r.$$('.card button, .card input, .card [role=slider]').length, 0);
  });
}

test('an unknown style with a non-number value is read only', () => {
  const { r } = withControls([{ name: 'R', label: 'Ref', style: 'OP', value: '/project1/geo' }]);
  assert.equal(r.text('.card .row .ro'), '/project1/geo');
});

test('a missing value shows as empty', () => {
  const { r } = withControls([{ name: 'R', label: 'R', style: 'Str' }]);
  assert.equal(r.text('.card .row .ro'), '');
});

test('an unknown style with a number value gets a slider', () => {
  // XY, RGB members etc. arrive one by one as numbers; they are treated like Floats.
  const { r } = withControls([{ name: 'Tx', label: 'Tx', style: 'XYZ', value: 0.5 }]);
  assert.ok(r.$('[role=slider]'));
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
  const { r, s, nodes } = panel();
  const sl = r.$('[role=slider]');
  const st = clone(STATE);
  st.controls.push({ name: 'New', label: 'New', style: 'Toggle', value: true });
  s.receive(st);
  assert.notEqual(r.$('[role=slider]'), sl);
  assert.equal(nodes().length, STATE.controls.length + 1);
});

test('a control changing style rebuilds the panel', () => {
  const { r, s } = panel();
  const st = clone(STATE);
  st.controls[IDX.Bypass] = { name: 'Bypass', label: 'Bypass', style: 'Pulse', section: false };
  s.receive(st);
  assert.equal(r.$('[role=switch]'), null);
});

test('reopening a patch after back builds it fresh', () => {
  const { r, s } = panel();
  const sl = r.$('[role=slider]');
  r.$('.back').click();
  r.$('.list button').click();
  s.receive(clone(STATE));
  assert.notEqual(r.$('[role=slider]'), sl);
});

test('an empty panel is just its title', () => {
  const { r } = withControls([]);
  assert.equal(r.title(), 'synth');
  assert.equal(r.$('.card').children.length, 0);
});

test('controls send to the patch they belong to', () => {
  const r = load({ stored: '123456' });
  const s = r.live();
  r.$$('.list button')[1].click();
  s.receive({ type: 'state', op: 'my_fx', controls: [{ name: 'On', label: 'On', style: 'Toggle', value: false }] });
  s.take();
  r.$('[role=switch]').click();
  assert.deepEqual(s.take(), [{ type: 'set', op: 'my_fx', par: 'On', value: true }]);
});
