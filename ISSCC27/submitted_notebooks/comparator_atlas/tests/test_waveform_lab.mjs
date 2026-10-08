import assert from "node:assert/strict";
import test from "node:test";
import { classify, inspectSample, interpolate, validateLab } from "../presentation/waveform_explorer.mjs";

function sample(id = "late") {
  const time = [-0.1, 0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1, 1.5, 2, 2.1];
  const qp = [1.8, 1.8, 1.8, 1.8, 1.7, 1.6, 1.5, 1.0, 0.9, 0.4, 0.1, 0.1];
  const qn = time.map(() => 1.8);
  return {
    id, label: "Synthetic contract example", description: "Tests only; not physical evidence.",
    source_kind: "schematic", point: { vdd_v: 1.8, differential_v: -0.001 },
    plot: { time_ns: time, qp_v: qp, qn_v: qn, clock_v: time.map(value => value > 0 ? 1.8 : 0) },
    observations: [
      { deadline_ns: 1, decision: 0, outcome: "unresolved", decision_time_ns: null,
        qp_at_deadline_v: 0.9, qn_at_deadline_v: 1.8, core_energy_fj: 100, reset_ok: true },
      { deadline_ns: 2, decision: -1, outcome: "correct", decision_time_ns: 1.6,
        qp_at_deadline_v: 0.1, qn_at_deadline_v: 1.8, core_energy_fj: 100, reset_ok: true },
    ],
  };
}

function fixture() {
  return { schema: 1, new_physical_simulations: 0, deadlines_ns: [1, 2], sample_count: 1,
    rail_thresholds_vdd: { high: 0.8, low: 0.2 }, samples: [sample()] };
}

test("both output rails are mandatory, not just a large differential", () => {
  assert.deepEqual(classify(1.8, 0.5, 1.8, 0.001), { decision: 0, outcome: "unresolved" });
  assert.deepEqual(classify(1.8, 0.1, 1.8, -0.001), { decision: 1, outcome: "wrong" });
  assert.deepEqual(classify(0.1, 1.8, 1.8, -0.001), { decision: -1, outcome: "correct" });
  assert.deepEqual(classify(0.1, 1.8, 1.8, 0), { decision: -1, outcome: "reference" });
});

test("changing the deadline changes the interpretation of the same trace, not its energy", () => {
  const data = validateLab(fixture());
  const early = inspectSample(data, "late", 1);
  const later = inspectSample(data, "late", 2);
  assert.equal(early.outcome, "unresolved");
  assert.equal(later.outcome, "correct");
  assert.equal(early.reading.core_energy_fj, later.reading.core_energy_fj);
  assert.equal(early.sample, later.sample);
});

test("recorded measurement and chart voltage disagreement fails explicitly", () => {
  const data = fixture();
  data.samples[0].observations[0].qp_at_deadline_v = 0.1;
  assert.throws(() => validateLab(data), /cursor voltages/);
});

test("recorded success is rejected when the physical rail contract says unresolved", () => {
  const data = fixture();
  data.samples[0].observations[0].outcome = "correct";
  assert.throws(() => validateLab(data), /decision contract/);
});

test("missing deadlines and duplicate samples are not replaced by a neighboring example", () => {
  const data = fixture();
  assert.throws(() => inspectSample(data, "absent", 1), /Unknown/);
  assert.throws(() => inspectSample(data, "late", 3.5), /recorded/);
  data.samples.push(sample()); data.sample_count++;
  assert.throws(() => validateLab(data), /duplicated|identifier/);
});

test("nonfinite, reordered or incomplete trace data cannot be displayed as evidence", () => {
  for (const mutate of [
    data => { data.samples[0].plot.time_ns[3] = data.samples[0].plot.time_ns[2]; },
    data => { data.samples[0].plot.qp_v[3] = Number.NaN; },
    data => { data.samples[0].plot.qn_v.pop(); },
  ]) {
    const data = fixture(); mutate(data);
    assert.throws(() => validateLab(data), /Waveform/);
  }
});

test("zero or negative supplies and unrecorded interpolation ranges are invalid", () => {
  assert.throws(() => classify(1, 0, 0, 1), /positive supply/);
  assert.throws(() => interpolate([0, 1], [0, 1], 2), /outside/);
  assert.equal(interpolate([0, 1], [0, 2], 0.25), 0.5);
});

test("a failed reset or invented unresolved latency is not a circuit pass", () => {
  const data = fixture();
  data.samples[0].observations[0].reset_ok = false;
  assert.throws(() => validateLab(data), /reset/);
  const other = fixture();
  other.samples[0].observations[0].decision_time_ns = 0;
  assert.throws(() => validateLab(other), /invented/);
});
