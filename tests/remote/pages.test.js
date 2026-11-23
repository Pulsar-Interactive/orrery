// Static checks on the two pages, and the QR page as Show QR fills it in.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';
import { REMOTE, PAIR } from './harness.js';

function fillPair(url, address, code) {
  // the same three replacements orrery_settings.show_qr() makes
  return PAIR.replaceAll('{{URL}}', url).replaceAll('{{ADDRESS}}', address).replaceAll('{{CODE}}', code);
}

test('the remote is one self-contained page', () => {
  assert.doesNotMatch(REMOTE, /<script[^>]+src=/);
  assert.doesNotMatch(REMOTE, /<link[^>]+href="(?!data:)/); // data: URIs (the icon) are inline
  assert.doesNotMatch(REMOTE, /@import|url\(http/);
});

test('the remote never writes HTML from data', () => {
  assert.doesNotMatch(REMOTE, /innerHTML|outerHTML|insertAdjacentHTML|document\.write/);
  assert.doesNotMatch(REMOTE, /\beval\(|new Function/);
});

test('the remote is set up for phones', () => {
  assert.match(REMOTE, /name="viewport" content="[^"]*viewport-fit=cover/);
  assert.match(REMOTE, /apple-mobile-web-app-capable/);
  assert.match(REMOTE, /<html lang="en">/);
});

test('the only outside link is the project page, opened safely', () => {
  const links = [...REMOTE.matchAll(/<a [^>]*>/g)].map((m) => m[0]);
  assert.equal(links.length, 1);
  assert.match(links[0], /href="https:\/\/github\.com\/Pulsar-Interactive\/orrery"/);
  assert.match(links[0], /rel="noopener"/);
});

test('the product is never named TouchDesigner', () => {
  for (const page of [REMOTE, PAIR]) {
    const title = page.match(/<title>(.*?)<\/title>/)[1];
    assert.doesNotMatch(title, /TouchDesigner/);
    assert.match(title, /Orrery/);
  }
});

test('both pages use the same brand colours', () => {
  for (const colour of ['#0E1214', '#4FD3DE', '#E8EDEF', '#9AA6AB']) {
    assert.ok(REMOTE.includes(colour), colour);
    assert.ok(PAIR.includes(colour), colour);
  }
});

test('the QR page has exactly the placeholders Show QR fills', () => {
  assert.deepEqual([...new Set([...PAIR.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]))].sort(), ['ADDRESS', 'CODE', 'URL']);
});

test('the QR library is pinned with subresource integrity', () => {
  const tag = PAIR.match(/<script src="[^"]+"[^>]*>/)[0];
  assert.match(tag, /^<script src="https:\/\//);
  assert.match(tag, /integrity="sha384-[A-Za-z0-9+/=]+"/);
  assert.match(tag, /crossorigin="anonymous"/);
});

test('the QR encodes the address with the code', () => {
  let made = null;
  const dom = new JSDOM(fillPair('http://192.168.1.20:9980/?code=042137', 'http://192.168.1.20:9980', '042137'), {
    runScripts: 'dangerously',
    beforeParse(window) {
      window.QRCode = function QRCode(el, opts) { made = { el, opts }; };
      window.QRCode.CorrectLevel = { M: 'M' };
    },
  });
  assert.equal(made.opts.text, 'http://192.168.1.20:9980/?code=042137');
  assert.equal(made.opts.correctLevel, 'M');
  assert.equal(made.el, dom.window.document.getElementById('qr'));
});

test('without the internet the address and code are still shown', () => {
  const dom = new JSDOM(fillPair('http://10.0.0.2:9980/?code=111222', 'http://10.0.0.2:9980', '111222'), { runScripts: 'dangerously' });
  const doc = dom.window.document;
  assert.equal(doc.querySelector('.addr').textContent, 'http://10.0.0.2:9980');
  assert.equal(doc.querySelector('.code').textContent, '111222');
  assert.equal(doc.getElementById('qr').childElementCount, 0);
});
