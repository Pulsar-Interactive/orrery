// Pairing: entering a code, codes from the QR, a code the component refuses.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { load } from './harness.js';

test('without a code it asks for one and opens no socket', () => {
  const r = load();
  assert.equal(r.sockets.length, 0);
  assert.equal(r.title(), 'Pair this phone');
  assert.ok(r.$('#code'));
  assert.equal(r.$('#status').hidden, true);
  assert.match(r.text('.hint'), /Pairing Code shown on the TD Remote component/);
});

test('the code field takes digits only and Connect waits for six', () => {
  const r = load();
  const input = r.$('#code');
  const go = r.button('CONNECT');
  assert.equal(go.disabled, true);
  r.type(input, '12a3-4 5');
  assert.equal(input.value, '12345');
  assert.equal(go.disabled, true);
  r.type(input, '123456');
  assert.equal(go.disabled, false);
  r.type(input, '12345');
  assert.equal(go.disabled, true);
});

test('code field is a numeric one-time code field', () => {
  const r = load();
  const input = r.$('#code');
  assert.equal(input.getAttribute('inputmode'), 'numeric');
  assert.equal(input.getAttribute('autocomplete'), 'one-time-code');
  assert.equal(input.getAttribute('maxlength'), '6');
  assert.equal(input.getAttribute('aria-label'), 'Pairing code');
  assert.equal(r.doc.activeElement, input);
});

test('Connect saves the code and opens the socket with it', () => {
  const r = load();
  r.type(r.$('#code'), '042137');
  r.button('CONNECT').click();
  assert.equal(r.window.localStorage.getItem('td-remote-code'), '042137');
  assert.equal(r.sockets.length, 1);
  assert.equal(r.ws().url, 'ws://192.168.1.20:9980/?code=042137');
  assert.equal(r.$('#status').hidden, false);
});

test('Enter submits a full code', () => {
  const r = load();
  const input = r.$('#code');
  r.type(input, '123456');
  input.dispatchEvent(new r.window.KeyboardEvent('keydown', { key: 'Enter' }));
  assert.equal(r.sockets.length, 1);
});

test('Enter with a short code does nothing', () => {
  const r = load();
  const input = r.$('#code');
  r.type(input, '123');
  input.dispatchEvent(new r.window.KeyboardEvent('keydown', { key: 'Enter' }));
  assert.equal(r.sockets.length, 0);
  assert.equal(r.window.localStorage.getItem('td-remote-code'), null);
});

test('a code from the QR is saved, used, and dropped from the address bar', () => {
  const r = load({ url: 'http://10.0.0.5:9980/?code=555111' });
  assert.equal(r.window.localStorage.getItem('td-remote-code'), '555111');
  assert.equal(r.window.location.search, '');
  assert.equal(r.window.location.pathname, '/');
  assert.equal(r.ws().url, 'ws://10.0.0.5:9980/?code=555111');
});

test('a QR code replaces a saved one', () => {
  const r = load({ url: 'http://10.0.0.5:9980/?code=222222', stored: '111111' });
  assert.equal(r.window.localStorage.getItem('td-remote-code'), '222222');
  assert.match(r.ws().url, /code=222222$/);
});

test('a saved code connects straight away', () => {
  const r = load({ stored: '987654' });
  assert.equal(r.ws().url, 'ws://192.168.1.20:9980/?code=987654');
  assert.notEqual(r.title(), 'Pair this phone');
});

test('the code is URL-encoded in the socket address', () => {
  const r = load({ url: 'http://h:1/?code=' + encodeURIComponent('1 2&x=3') });
  assert.equal(r.ws().url, 'ws://h:1/?code=1%202%26x%3D3');
});

test('the socket goes to the host the page came from, port included', () => {
  const r = load({ url: 'http://studio.local:12345/index.html', stored: '123456' });
  assert.equal(r.ws().url, 'ws://studio.local:12345/?code=123456');
});

test('a refused code is forgotten and the phone asks again, without reconnecting', () => {
  const r = load({ stored: '000000' });
  const s = r.ws();
  s.accept().receive({ type: 'denied' });
  assert.equal(s.closed, true);
  assert.equal(r.window.localStorage.getItem('td-remote-code'), null);
  assert.equal(r.title(), 'Pair this phone');
  assert.match(r.text('.hint.error'), /not accepted/);
  r.advance(10_000);
  assert.equal(r.sockets.length, 1, 'no retry loop with a bad code');
  assert.match(r.text('.hint.error') ?? '', /not accepted/, 'the message stays until a new code is entered');
  assert.equal(r.$('#status').hidden, true);
});

test('after a refusal a new code pairs', () => {
  const r = load({ stored: '000000' });
  r.ws().accept().receive({ type: 'denied' });
  r.type(r.$('#code'), '123456');
  r.button('CONNECT').click();
  assert.equal(r.sockets.length, 2);
  assert.match(r.ws().url, /code=123456$/);
  r.ws().accept();
  assert.equal(r.text('#status'), 'CONNECTED');
});

test('denied while on a panel goes back to pairing', () => {
  const r = load({ stored: '123456' });
  const s = r.openPanel();
  s.receive({ type: 'denied' });
  assert.equal(r.title(), 'Pair this phone');
  assert.equal(r.$('.back'), null);
});

test('storage that throws (private mode) still lets the phone pair', () => {
  const r = load();
  Object.defineProperty(r.window, 'localStorage', { get() { throw new Error('denied'); } });
  r.type(r.$('#code'), '123456');
  r.button('CONNECT').click();
  assert.match(r.ws().url, /code=123456$/);
});
