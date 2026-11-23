// The socket: status, reconnecting, coming back from a locked phone, the wake lock.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { load, STATE, clone } from './harness.js';

test('opening the socket shows CONNECTED and asks for the list', () => {
  const r = load({ stored: '123456' });
  assert.equal(r.text('#status'), 'CONNECTING');
  r.ws().accept();
  assert.equal(r.text('#status'), 'CONNECTED');
  assert.equal(r.$('#status').className, 'dot live');
  assert.deepEqual(r.ws().take(), [{ type: 'list' }]);
});

test('a dropped socket shows OFFLINE and retries after two seconds', () => {
  const r = load({ stored: '123456' });
  r.live().drop();
  assert.equal(r.text('#status'), 'OFFLINE');
  assert.equal(r.$('#status').className, 'dot off');
  r.advance(1999);
  assert.equal(r.sockets.length, 1);
  r.advance(1);
  assert.equal(r.sockets.length, 2);
  assert.match(r.ws().url, /code=123456$/);
});

test('it keeps retrying while the computer is away', () => {
  const r = load({ stored: '123456' });
  r.ws().drop();
  for (let i = 2; i <= 5; i++) {
    r.advance(2000);
    assert.equal(r.sockets.length, i);
    r.ws().drop();
  }
});

test('reconnecting on a panel asks for that panel again', () => {
  const r = load({ stored: '123456' });
  r.openPanel().drop();
  r.advance(2000);
  r.ws().accept();
  assert.deepEqual(r.ws().take(), [{ type: 'list' }, { type: 'get', op: 'synth' }]);
});

test('the panel stays on screen while reconnecting', () => {
  const r = load({ stored: '123456' });
  r.openPanel().drop();
  assert.equal(r.title(), 'synth');
  assert.ok(r.$('[role=slider]'));
});

test('a list arriving after reconnecting does not leave the panel', () => {
  const r = load({ stored: '123456' });
  r.openPanel().drop();
  r.advance(2000);
  r.live();
  assert.equal(r.title(), 'synth');
});

test('coming back to the page reconnects at once if the socket died', () => {
  const r = load({ stored: '123456' });
  const s = r.live();
  s.readyState = 3; // the phone locked; no close event arrived
  r.doc.dispatchEvent(new r.window.Event('visibilitychange'));
  assert.equal(r.sockets.length, 2);
});

test('coming back with a healthy socket does nothing', () => {
  const r = load({ stored: '123456' });
  r.live();
  r.doc.dispatchEvent(new r.window.Event('visibilitychange'));
  assert.equal(r.sockets.length, 1);
});

test('coming back while still connecting does nothing', () => {
  const r = load({ stored: '123456' });
  r.doc.dispatchEvent(new r.window.Event('visibilitychange'));
  assert.equal(r.sockets.length, 1);
});

test('coming back with no code does nothing', () => {
  const r = load();
  r.doc.dispatchEvent(new r.window.Event('visibilitychange'));
  assert.equal(r.sockets.length, 0);
});

test('an early reconnect cancels the pending retry', () => {
  const r = load({ stored: '123456' });
  const s = r.ws();
  s.drop();
  s.readyState = 3;
  r.doc.dispatchEvent(new r.window.Event('visibilitychange'));
  assert.equal(r.sockets.length, 2);
  r.advance(5000);
  assert.equal(r.sockets.length, 2, 'the old 2 s timer was cleared');
});

test('taps while disconnected are dropped, not thrown, and the switch does not flip', () => {
  const r = load({ stored: '123456' });
  const s = r.openPanel();
  s.drop();
  const sw = r.$('[role=switch]');
  assert.doesNotThrow(() => sw.click());
  assert.deepEqual(s.sent, []);
  assert.equal(sw.getAttribute('aria-checked'), 'false');
});

test('offline, a banner says so and the controls are locked until it reconnects', () => {
  const r = load({ stored: '123456' });
  r.openPanel().drop();
  assert.equal(r.$('#banner').hidden, false);
  assert.match(r.text('#banner'), /Not connected to TouchDesigner/);
  assert.ok(r.doc.body.classList.contains('offline'));
  r.advance(2000);
  r.ws().accept();
  assert.equal(r.$('#banner').hidden, true);
  assert.ok(!r.doc.body.classList.contains('offline'));
});

test('offline, the stepper does not change', () => {
  const r = load({ stored: '123456' });
  const s = r.openPanel();
  s.drop();
  r.button('Voices up').click();
  assert.equal(r.$('.step .val').textContent, '4');
  assert.deepEqual(s.sent, []);
});

test('the first touch asks to keep the screen on, once', () => {
  const r = load({ stored: '123456' });
  const asked = [];
  Object.defineProperty(r.window.navigator, 'wakeLock', {
    value: { request: (k) => { asked.push(k); return Promise.resolve({}); } }, configurable: true,
  });
  r.fire(r.doc.body, 'pointerdown');
  r.fire(r.doc.body, 'pointerdown');
  assert.deepEqual(asked, ['screen']);
});

test('a refused wake lock is swallowed', async () => {
  const r = load({ stored: '123456' });
  Object.defineProperty(r.window.navigator, 'wakeLock', {
    value: { request: () => Promise.reject(new Error('NotAllowed')) }, configurable: true,
  });
  r.fire(r.doc.body, 'pointerdown');
  await new Promise((res) => setImmediate(res));
});

test('browsers without a wake lock are fine', () => {
  const r = load({ stored: '123456' });
  assert.doesNotThrow(() => r.fire(r.doc.body, 'pointerdown'));
});

test('state that arrives before anything is opened is ignored', () => {
  const r = load({ stored: '123456' });
  const s = r.live();
  s.receive(clone(STATE));
  assert.equal(r.$('[role=slider]'), null);
  assert.equal(r.title(), 'show');
});
