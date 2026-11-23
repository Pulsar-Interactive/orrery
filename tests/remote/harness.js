// Loads td/remote.html in jsdom with a fake WebSocket and a fake clock, so each test can play
// the part of the Orrery component and of the person holding the phone.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';

const root = fileURLToPath(new URL('../../', import.meta.url));
export const REMOTE = readFileSync(root + 'td/remote.html', 'utf8');
export const PAIR = readFileSync(root + 'td/pair.html', 'utf8');
export const STATE = JSON.parse(readFileSync(root + 'tests/fixtures/synth_state.json', 'utf8'));
export const LIST = { type: 'list', project: 'show', patches: [
  { op: 'synth', label: 'synth', count: STATE.controls.length },
  { op: 'my_fx', label: 'my fx', count: 1 },
] };

export function clone(x) { return JSON.parse(JSON.stringify(x)); }

export function load({ url = 'http://192.168.1.20:9980/', stored = null } = {}) {
  const sockets = [];
  const clock = { now: 1_000_000, timers: [], nextId: 1 };

  const dom = new JSDOM(REMOTE, {
    url,
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    beforeParse(window) {
      if (stored !== null) window.localStorage.setItem('orrery-code', stored);

      window.Date.now = () => clock.now;
      window.setTimeout = (fn, ms = 0) => {
        const id = clock.nextId++;
        clock.timers.push({ id, at: clock.now + ms, fn });
        return id;
      };
      window.clearTimeout = (id) => { clock.timers = clock.timers.filter((t) => t.id !== id); };

      class FakeWebSocket {
        constructor(u) {
          this.url = u; this.readyState = 0; this.sent = []; this.closed = false;
          sockets.push(this);
        }
        send(text) { if (this.readyState !== 1) throw new Error('send before open'); this.sent.push(JSON.parse(text)); }
        // like a browser: closing fires the close event (here at once rather than on a later task)
        close() { if (this.closed) return; this.closed = true; this.readyState = 3; this.onclose?.(); }
        // the server side
        accept() { this.readyState = 1; this.onopen?.(); return this; }
        receive(msg) { this.onmessage?.({ data: JSON.stringify(msg) }); return this; }
        drop() { this.readyState = 3; this.onclose?.(); }
        take() { const s = this.sent; this.sent = []; return s; }
      }
      window.WebSocket = FakeWebSocket;
    },
  });

  const { window } = dom;
  const doc = window.document;
  const $ = (sel) => doc.querySelector(sel);
  const $$ = (sel) => [...doc.querySelectorAll(sel)];
  const text = (sel) => $(sel)?.textContent;

  function advance(ms) {
    const until = clock.now + ms;
    for (;;) {
      clock.timers.sort((a, b) => a.at - b.at);
      const t = clock.timers[0];
      if (!t || t.at > until) break;
      clock.timers.shift();
      clock.now = t.at;
      t.fn();
    }
    clock.now = until;
  }

  const ws = () => sockets[sockets.length - 1];

  // Pair, accept and show the list: the usual start of a test.
  function live(list = LIST) {
    const s = ws().accept();
    s.receive(clone(list));
    s.take();
    return s;
  }

  function openPanel(state = STATE) {
    const s = live();
    const btn = $$('.list button').find((b) => b.textContent.startsWith(state.op === 'synth' ? 'synth' : state.op));
    btn.click();
    s.receive(clone(state));
    s.take();
    return s;
  }

  function button(label) {
    return $$('button').find((b) => b.textContent.trim() === label || b.getAttribute('aria-label') === label);
  }

  function rowOf(label) {
    return $$('.ctl, .row, .ghost').find((n) => n.firstElementChild?.textContent === label || n.textContent.startsWith(label));
  }

  function fire(node, type, init = {}) {
    const e = new window.Event(type, { bubbles: true, cancelable: true, ...init });
    node.dispatchEvent(e);
    return e;
  }

  function type(input, value) {
    input.value = value;
    fire(input, 'input');
  }

  return { dom, window, doc, $, $$, text, sockets, ws, clock, advance, live, openPanel, button, rowOf, fire, type };
}
