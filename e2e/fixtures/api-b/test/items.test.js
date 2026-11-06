import assert from "node:assert/strict";
import test from "node:test";
import { handle } from "../src/app.js";

test("GET /items lists items", () => {
  const r = handle("GET", "/items");
  assert.equal(r.status, 200);
  assert.equal(r.body.length, 2);
});

test("GET /items/:id returns one item or 404", () => {
  assert.equal(handle("GET", "/items/1").body.name, "parafuso");
  assert.equal(handle("GET", "/items/99").status, 404);
});
