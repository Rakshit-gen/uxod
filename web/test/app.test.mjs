// Loads app.js against a stand-in DOM and drives it, since there is no
// browser in CI: catches errors at load, in frames, and in share links.
import assert from "node:assert/strict";
import { test } from "node:test";

function element(id) {
  const el = {
    id, textContent: "", value: "", innerHTML: "", children: [], files: [], elements: [],
    classList: { toggle() {} },
    tBodies: [{ innerHTML: "" }],
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 600 }),
    getContext: () => new Proxy({}, { get: () => () => {}, set: () => true }),
  };
  return el;
}

const els = new Map();
const frames = [];
globalThis.devicePixelRatio = 1;
globalThis.document = {
  getElementById: (id) => els.get(id) || els.set(id, element(id)).get(id),
  querySelectorAll: () => [],
};
globalThis.addEventListener = () => {};
globalThis.requestAnimationFrame = (f) => frames.push(f);
globalThis.setInterval = () => 0;
globalThis.setTimeout = () => 0;
globalThis.history = { replaceState(_, __, url) { globalThis.location.hash = url.slice(url.indexOf("#")); } };
globalThis.location = { origin: "https://example.test", pathname: "/", hash: "" };
Object.defineProperty(globalThis, "navigator", { value: { clipboard: { writeText: async () => {} } } });

const run = (n, ms = 16) => {
  for (let k = 0; k < n; k++) {
    const f = frames.shift();
    f((k + 1) * ms);
  }
};

test("the page loads, plays and makes a link that replays", async () => {
  await import("../app.js");
  run(30);
  assert.match(document.getElementById("year").textContent, /^year \d+\.\d$/);
  document.getElementById("remove").onclick();  // deletes Earth, the default pick
  run(5);
  assert.equal(document.getElementById("error").textContent, "");
  await document.getElementById("share").onclick();
  const hash = location.hash;
  assert.ok(hash.startsWith("#plan="));
  const saved = JSON.parse(decodeURIComponent(escape(atob(hash.slice(6)))));
  assert.deepEqual(saved.plan.map((s) => s.tool), ["run", "remove_body", "run"]);
  assert.equal(saved.plan[1].args.name, "Earth");
});
