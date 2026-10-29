// Checks the page against the files it expects to find.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";

const page = readFileSync(new URL("../index.html", import.meta.url), "utf8");

test("every scenario in the menu is an example plan", () => {
  const menu = page.slice(page.indexOf('<select id="preset">'), page.indexOf("</select>", page.indexOf('id="preset"')));
  const presets = [...menu.matchAll(/<option value="([a-z-]+)">/g)].map((m) => m[1]);
  assert.ok(presets.length >= 5);
  for (const name of presets) {
    assert.ok(existsSync(new URL(`../../examples/${name}.json`, import.meta.url)), `${name}.json is missing`);
  }
});
