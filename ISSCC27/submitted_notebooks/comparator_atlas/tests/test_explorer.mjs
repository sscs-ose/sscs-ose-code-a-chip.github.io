import assert from "node:assert/strict";
import test from "node:test";
import { filterRows, summarize, validateCube } from "../comparator_atlas/assets/explorer.mjs";

function fixture() {
  return {
    designs: ["baseline"], cases: ["training", "reserved"], policies: ["local_boundary"],
    deadlines: [1], inputs: [-1, 0, 1], trainingCases: [0],
    rows: [
      [0, 0, 0, 0, 0, 2, 0.5, 100, -2],
      [0, 0, 0, 0, 1, 4, null, 110, -2],
      [0, 0, 0, 0, 2, 0, 0.4, 100, -2],
      [0, 1, 0, 0, 0, 3, null, null, null],
      [0, 1, 0, 0, 1, 4, null, null, null],
      [0, 1, 0, 0, 2, 2, 0.6, 120, -3],
    ],
  };
}

test("zero input is excluded and unavailable calibration is not dropped", () => {
  const cube = validateCube(fixture());
  const records = filterRows(cube, { design: 0, policy: 0, deadline: 0, reservedOnly: false });
  assert.deepEqual(summarize(cube, records, 1), { total: 4, correct: 2, fraction: 0.5, unavailable: 1 });
});

test("reserved scope excludes selection conditions without changing outcomes", () => {
  const cube = fixture();
  const records = filterRows(cube, { design: 0, policy: 0, deadline: 0, reservedOnly: true });
  assert.deepEqual(summarize(cube, records, 1), { total: 2, correct: 1, fraction: 0.5, unavailable: 1 });
});

test("an empty score band is not a passing result", () => {
  const cube = fixture();
  assert.deepEqual(summarize(cube, cube.rows, 30), { total: 0, correct: 0, fraction: null, unavailable: 0 });
});

test("missing and duplicated observations are rejected", () => {
  const missing = fixture();
  missing.rows.pop();
  assert.throws(() => validateCube(missing), /declared grid/);
  const duplicate = fixture();
  duplicate.rows[5] = duplicate.rows[0];
  assert.throws(() => validateCube(duplicate), /Duplicate/);
});

test("invalid controls cannot silently select a different dataset", () => {
  assert.throws(() => filterRows(fixture(), { design: -1, policy: 0, deadline: 0 }), /selection/);
  assert.throws(() => summarize(fixture(), [], Number.NaN), /guardband/);
});
