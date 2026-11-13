import assert from "node:assert/strict";
import test from "node:test";
import { comparisonRows, hasConflictingValues } from "../lib/comparison.ts";

test("comparison preserves conflicts and represents missing evidence with an empty cell", () => {
  const depth = (id, value) => ({ id, key: "depth_rating", label: "Depth rating", value, unit: "m" });
  const first = { specifications: [depth(1, "300"), depth(2, "600")] };
  const second = { specifications: [] };
  const [row] = comparisonRows([first, second]);
  assert.equal(row.key, "depth_rating");
  assert.deepEqual(row.cells[0], first.specifications);
  assert.deepEqual(row.cells[1], []);
  assert.equal(hasConflictingValues(row.cells[0]), true);
  assert.equal(hasConflictingValues(row.cells[1]), false);
  assert.equal(hasConflictingValues([depth(1, "300"), depth(3, "300")]), false);
});
