// The top bar on a patch's screen (GO LIVE / ON AIR and REC) and the SHOW section of the list.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { load, LIST, STATE, clone } from './harness.js';

// LIST with On Air settable for synth only, and a recorder (or not).
function list({ live = '', recording = null, canLive = ['synth'] } = {}) {
  const l = clone(LIST);
  l.live = live;
  l.recording = recording;
  for (const p of l.patches) p.canLive = canLive.includes(p.op);
  return l;
}

function onPanel(l) {
  const r = load({ stored: '123456' });
  const s = r.live(l);
  r.$$('.list button')[0].click(); // synth
  s.receive(clone(STATE));
  s.take();
  const play = r.$('#play'), rec = r.$('#rec'), bar = r.$('#transport');
  return { r, s, play, rec, bar };
}

// --- GO LIVE ---------------------------------------------------------------------------------

test('the list has no transport bar', () => {
  const r = load({ stored: '123456' });
  r.live(list({ recording: false }));
  assert.equal(r.$('#transport').hidden, true);
});

test('a patch that can go live shows GO LIVE, and tapping it asks to go live', () => {
  const { s, play, bar } = onPanel(list());
  assert.equal(bar.hidden, false);
  assert.equal(play.hidden, false);
  assert.equal(play.textContent, '▶ GO LIVE');
  play.click();
  assert.deepEqual(s.take(), [{ type: 'live', op: 'synth' }]);
});

test('the patch on air shows ON AIR and tapping it sends nothing', () => {
  const { s, play } = onPanel(list({ live: 'synth' }));
  assert.equal(play.textContent, 'ON AIR');
  assert.match(play.className, /\bon\b/);
  play.click();
  assert.deepEqual(s.take(), []);
});

test('going live from another phone updates this one', () => {
  const { s, play } = onPanel(list());
  s.receive(list({ live: 'synth' }));
  assert.equal(play.textContent, 'ON AIR');
  s.receive(list({ live: 'my_fx' }));
  assert.equal(play.textContent, '▶ GO LIVE');
});

test('a patch that can not go live and no recorder: no bar at all', () => {
  const { play, bar } = onPanel(list({ canLive: [] }));
  assert.equal(play.hidden, true);
  assert.equal(bar.hidden, true);
});

test('a refused GO LIVE explains why', () => {
  const { r, s, play } = onPanel(list());
  play.click();
  s.take();
  s.receive({ type: 'error', error: 'synth can not go live from here' });
  assert.match(r.text('#toast'), /Couldn't change what is on air\. synth can not go live from here/);
});

// --- REC -------------------------------------------------------------------------------------

test('no recorder: no REC button', () => {
  const { rec } = onPanel(list());
  assert.equal(rec.hidden, true);
});

test('REC starts recording, STOP REC stops it', () => {
  const { s, rec } = onPanel(list({ recording: false }));
  assert.equal(rec.hidden, false);
  assert.equal(rec.textContent, 'REC');
  assert.equal(rec.getAttribute('aria-pressed'), 'false');
  rec.click();
  assert.deepEqual(s.take(), [{ type: 'record', on: true }]);
  s.receive(list({ recording: true }));
  assert.equal(rec.textContent, 'STOP REC');
  assert.equal(rec.getAttribute('aria-pressed'), 'true');
  rec.click();
  assert.deepEqual(s.take(), [{ type: 'record', on: false }]);
});

test('REC shows on every patch, even one that can not go live', () => {
  const { play, rec, bar } = onPanel(list({ recording: false, canLive: [] }));
  assert.equal(play.hidden, true);
  assert.equal(rec.hidden, false);
  assert.equal(bar.hidden, false);
});

test('going back to the list hides the bar', () => {
  const { r, bar } = onPanel(list({ recording: false }));
  r.$('.back').click();
  assert.equal(bar.hidden, true);
});

// --- SHOW section ----------------------------------------------------------------------------

test('nothing tagged td-remote-show: one list, no section labels', () => {
  const r = load({ stored: '123456' });
  r.live(list());
  assert.equal(r.$$('.list').length, 1);
  assert.deepEqual(r.$$('#main .group').map((g) => g.textContent), []);
});

test('show-wide COMPs get a SHOW section above the patches', () => {
  const r = load({ stored: '123456' });
  const l = list();
  l.patches.push({ op: 'sound', label: 'sound', count: 2, show: true });
  r.live(l);
  assert.deepEqual(r.$$('#main .group').map((g) => g.textContent), ['SHOW', 'PATCHES']);
  const [showList, patchList] = r.$$('.list');
  assert.deepEqual([...showList.querySelectorAll('.name > span:first-child')].map((n) => n.textContent), ['sound']);
  assert.deepEqual([...patchList.querySelectorAll('.name > span:first-child')].map((n) => n.textContent), ['synth', 'my fx']);
});

test('show items have no status pip, patches do', () => {
  const r = load({ stored: '123456' });
  const l = list();
  l.patches.push({ op: 'sound', label: 'sound', count: 2, show: true });
  r.live(l);
  const [showList, patchList] = r.$$('.list');
  assert.equal(showList.querySelector('.pip'), null);
  assert.ok(patchList.querySelector('.pip'));
});

test('only show-wide COMPs: no PATCHES label', () => {
  const r = load({ stored: '123456' });
  r.live({ type: 'list', project: 'show', patches: [{ op: 'sound', label: 'sound', count: 2, show: true }] });
  assert.deepEqual(r.$$('#main .group').map((g) => g.textContent), ['SHOW']);
});

test('a show item opens like any patch', () => {
  const r = load({ stored: '123456' });
  const s = r.live({ type: 'list', project: 'show', patches: [{ op: 'sound', label: 'sound', count: 2, show: true }] });
  r.$('.list button').click();
  assert.deepEqual(s.take(), [{ type: 'get', op: 'sound' }]);
});
