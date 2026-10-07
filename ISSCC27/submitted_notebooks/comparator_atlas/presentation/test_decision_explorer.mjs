import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { selection, witnesses } from "./decision_explorer.mjs";
import { validateCube } from "../comparator_atlas/assets/explorer.mjs";
import { validateLab } from "./waveform_explorer.mjs";

const data = JSON.parse(fs.readFileSync(new URL("../results/study/decision_data.json", import.meta.url)));
test("36 exact selections,108 count closures,nulls and all witnesses", () => {
  for (const minimum of data.minimums) for (const deadline of data.deadlines) {
    const result = selection(data, minimum, deadline);
    assert.deepEqual(result.choice, data.selections.find(r => r.minimum_abs_input_mv === minimum && r.deadline_ns === deadline));
    for (const row of result.candidates) {
      const records = witnesses(data, minimum, deadline, row.design);
      assert.equal(records.length, row.wrong + row.unresolved);
      assert.equal(records.filter(r => r.outcome === "wrong").length, row.wrong);
      assert.equal(records.filter(r => r.outcome === "unresolved").length, row.unresolved);
      for (const record of records) {
        assert.equal(record.outcome === "unresolved", record.decision_time_ns === null);
      }
    }
    if (result.choice.winner === null) assert.equal(result.choice.sampled_limits, null);
  }
});
test("1 ns presets and return transition remain correct", () => {
  assert.deepEqual([1, 3, 30, 1].map(band => selection(data, band, 1).choice.winner),
    [null, "lvt_balanced_4b", "lvt_base_3b", null]);
});
test("exact ties retain published design order; corrupted choices/closures fail explicitly", () => {
  const tied = structuredClone(data);
  const rows = tied.candidates.filter(r => r.minimum_abs_input_mv === 30 && r.deadline_ns === 1 && r.all_correct);
  rows.forEach(r => { r.mean_core_energy_fj = 150; });
  const choice = tied.selections.find(r => r.minimum_abs_input_mv === 30 && r.deadline_ns === 1);
  Object.assign(choice, { winner: "lvt_balanced_4b", mean_core_energy_fj: 150,
    minimum_energy_ties: ["lvt_balanced_4b", "lvt_base_3b"] });
  assert.deepEqual(selection(tied, 30, 1).choice.minimum_energy_ties, choice.minimum_energy_ties);
  const bad = structuredClone(data);
  bad.candidates[0].unresolved++;
  assert.throws(() => selection(bad, data.minimums[0], data.deadlines[0]), /closure/);
  assert.throws(() => selection(data, 2, 1), /sampled/);
  assert.throws(() => selection(data, 1, 1.5), /sampled/);
});
test("reused map/lab accept exact complete saved grids without missing control policies", () => {
  validateCube(JSON.parse(fs.readFileSync(new URL("../results/study/decision_map_data.json", import.meta.url))));
  validateLab(JSON.parse(fs.readFileSync(new URL("../evidence_traces/waveform_lab/waveform_lab.json", import.meta.url))));
});
