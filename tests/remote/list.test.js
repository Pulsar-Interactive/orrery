// The list of patches, opening one, going back, patches that disappear.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { load, LIST, STATE, clone } from './harness.js';

test('the list shows the project and each patch with its control count', () => {
  const r = load({ stored: '123456' });
  r.live();
  assert.equal(r.text('h1'), 'show');
  const rows = r.$$('.list button').map((b) => [...b.children].map((c) => c.textContent));
  assert.deepEqual(rows, [['synth', '10 ›'], ['my fx', '1 ›']]);
});

test('no patches: explains how to add a Controls page', () => {
  const r = load({ stored: '123456' });
  r.live({ type: 'list', project: 'show', patches: [] });
  assert.equal(r.$('.list'), null);
  assert.match(r.text('.hint'), /custom parameter page named Controls/);
});

test('no project name: the heading says Controls', () => {
  const r = load({ stored: '123456' });
  r.live({ type: 'list', project: '', patches: [] });
  assert.equal(r.text('h1'), 'Controls');
});

test('a new list replaces the old one', () => {
  const r = load({ stored: '123456' });
  const s = r.live();
  s.receive({ type: 'list', project: 'show', patches: [{ op: 'lights', label: 'lights', count: 3 }] });
  assert.deepEqual(r.$$('.list button').map((b) => b.firstChild.textContent), ['lights']);
});

test('tapping a patch asks for its state', () => {
  const r = load({ stored: '123456' });
  const s = r.live();
  r.$$('.list button')[1].click();
  assert.deepEqual(s.take(), [{ type: 'get', op: 'my_fx' }]);
});

test('the panel opens when its state arrives, titled with the patch label', () => {
  const r = load({ stored: '123456' });
  const s = r.live();
  r.$$('.list button')[1].click();
  s.receive({ type: 'state', op: 'my_fx', controls: [{ name: 'Mix', label: 'Mix', style: 'Float', value: 0.5, min: 0, max: 1, default: 0 }] });
  assert.equal(r.text('h1'), 'my fx');
});

test('a panel with no label in the list is titled with its op name', () => {
  const r = load({ stored: '123456' });
  const s = r.live({ type: 'list', project: 'show', patches: [{ op: 'synth', label: 'synth', count: 1 }] });
  r.$('.list button').click();
  s.receive({ type: 'list', project: 'show', patches: [] });
  s.receive(clone(STATE));
  assert.equal(r.text('h1'), 'synth');
});

test('state for a different patch is ignored', () => {
  const r = load({ stored: '123456' });
  const s = r.live();
  r.$$('.list button')[1].click();
  s.receive(clone(STATE)); // op: synth
  assert.equal(r.text('h1'), 'show');
});

test('back returns to the list and refreshes it', () => {
  const r = load({ stored: '123456' });
  const s = r.openPanel();
  const back = r.$('.back');
  assert.equal(back.textContent, '‹ show');
  assert.equal(back.getAttribute('aria-label'), 'Back to the list');
  back.click();
  assert.equal(r.text('h1'), 'show');
  assert.deepEqual(s.take(), [{ type: 'list' }]);
  assert.equal(r.$('.back'), null);
});

test('back says Back when there is no project name', () => {
  const r = load({ stored: '123456' });
  const s = r.live({ type: 'list', project: '', patches: LIST.patches });
  r.$('.list button').click();
  s.receive(clone(STATE));
  assert.equal(r.text('.back'), '‹ Back');
});

test('after back, state for the old patch is ignored', () => {
  const r = load({ stored: '123456' });
  const s = r.openPanel();
  r.$('.back').click();
  s.receive(clone(STATE));
  assert.equal(r.text('h1'), 'show');
});

test('a patch that disappears sends the phone back to the list', () => {
  const r = load({ stored: '123456' });
  const s = r.openPanel();
  s.receive({ type: 'error', error: 'nothing to control called synth' });
  assert.equal(r.text('h1'), 'show');
});

test('other errors keep the panel', () => {
  const r = load({ stored: '123456' });
  const s = r.openPanel();
  s.receive({ type: 'error', error: 'not a control: Level' });
  assert.equal(r.text('h1'), 'synth');
});

test('errors on the list are harmless', () => {
  const r = load({ stored: '123456' });
  const s = r.live();
  s.receive({ type: 'error', error: 'nothing to control called x' });
  assert.equal(r.text('h1'), 'show');
});

test('unknown messages are ignored', () => {
  const r = load({ stored: '123456' });
  const s = r.live();
  s.receive({ type: 'future-thing', x: 1 });
  assert.equal(r.text('h1'), 'show');
});

test('names from TouchDesigner are shown as text, never as HTML', () => {
  const r = load({ stored: '123456' });
  const evil = '<img src=x onerror="window.pwned=1">';
  const s = r.live({ type: 'list', project: evil, patches: [{ op: 'a', label: evil, count: 1 }] });
  assert.equal(r.text('h1'), evil);
  assert.equal(r.$('img'), null);
  r.$('.list button').click();
  s.receive({ type: 'state', op: 'a', controls: [
    { name: 'H', label: evil, style: 'Header' },
    { name: 'S', label: evil, style: 'Str', value: evil },
    { name: 'M', label: evil, style: 'Menu', value: 'x', options: [['x', evil]] },
  ] });
  assert.equal(r.$('img'), null);
  assert.equal(r.window.pwned, undefined);
});
