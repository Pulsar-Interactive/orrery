// Static checks on the remote page. The QR is drawn inside the component now (tests/td/test_qr.py),
// so the remote is the only page the component serves.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { REMOTE } from './harness.js';

const WEB = readdirSync(fileURLToPath(new URL('../../td/web/', import.meta.url))).filter((f) => !f.startsWith('.'));

test('the remote loads nothing from the internet', () => {
  // it has to work on a show network with no internet: no CDN scripts, styles or fonts
  assert.doesNotMatch(REMOTE, /<script[^>]+src=/);
  assert.doesNotMatch(REMOTE, /<link[^>]+href="https?:/);
  assert.doesNotMatch(REMOTE, /<img[^>]+src="https?:/);
  assert.doesNotMatch(REMOTE, /@import|url\(["']?https?:/);
});

test('every file the remote links is one the component serves', () => {
  const linked = [...REMOTE.matchAll(/(?:href|src)="\/([\w.-]+)"/g)].map((m) => m[1]);
  assert.ok(linked.length >= 4, 'manifest, icons and the Pulsar logo');
  for (const name of linked) assert.ok(WEB.includes(name), name);
});

test('the remote never writes HTML from data', () => {
  assert.doesNotMatch(REMOTE, /innerHTML|outerHTML|insertAdjacentHTML|document\.write/);
  assert.doesNotMatch(REMOTE, /\beval\(|new Function/);
});

test('the remote is set up for phones', () => {
  assert.match(REMOTE, /name="viewport" content="[^"]*viewport-fit=cover/);
  assert.match(REMOTE, /apple-mobile-web-app-capable/);
  assert.match(REMOTE, /<link rel="manifest" href="\/manifest\.webmanifest"/);
  assert.match(REMOTE, /<html lang="en">/);
});

test('the only outside link is the project page, opened safely', () => {
  const links = [...REMOTE.matchAll(/<a [^>]*>/g)].map((m) => m[0]);
  assert.equal(links.length, 1);
  assert.match(links[0], /href="https:\/\/github\.com\/Pulsar-Interactive\/td-remote"/);
  assert.match(links[0], /rel="noopener"/);
});

test('the product is never named TouchDesigner', () => {
  const title = REMOTE.match(/<title>(.*?)<\/title>/)[1];
  assert.doesNotMatch(title, /TouchDesigner/);
  assert.match(title, /TD Remote/);
});

test('the remote uses the TD Remote colours', () => {
  // page, raised surfaces, Sol Amber (brand) and the cyan used for selection
  for (const colour of ['#111114', '#1C1C1C', '#FFB020', '#05F9FE']) assert.ok(REMOTE.includes(colour), colour);
  assert.match(REMOTE, /<meta name="theme-color" content="#111114">/);
});

test('the pairing code is never written into the page', () => {
  // the component serves the same page to everyone; the code only travels in the WebSocket URL
  assert.doesNotMatch(REMOTE, /\{\{\w+\}\}/);
  assert.doesNotMatch(REMOTE, /code=\d{6}/);
});
