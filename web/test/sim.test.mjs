// Checks the JavaScript simulation against the Python one on every example.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { replay } from "../tools.js";

const fixtures = JSON.parse(readFileSync(new URL("./fixtures.json", import.meta.url)));
const examples = new URL("../../examples/", import.meta.url);

for (const [name, want] of Object.entries(fixtures)) {
  test(`${name} matches the Python`, () => {
    const plan = JSON.parse(readFileSync(new URL(`${name}.json`, examples))).plan;
    const { universe, runs } = replay(plan);
    assert.deepEqual(runs.flatMap((r) => r.events), want.events);
    assert.deepEqual(runs.map((r) => r.steps), want.steps);
    assert.deepEqual(universe.bodies.map((b) => b.name), Object.keys(want.bodies));
    for (const b of universe.bodies) {
      const w = want.bodies[b.name];
      const off = Math.hypot(...b.pos.map((x, k) => x - w.pos[k]));
      assert.ok(off < 1e-6, `${b.name} is ${off} AU from where Python put it`);
    }
  });
}
