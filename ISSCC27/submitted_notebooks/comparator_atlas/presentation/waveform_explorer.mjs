const SVG_NS = "http://www.w3.org/2000/svg";
const OUTCOME_TEXT = {
  correct: "Correct: both required rails have been reached.",
  wrong: "Wrong polarity: resolved is not the same as correct.",
  unresolved: "Unresolved: at least one required rail has not been reached by the deadline.",
  reference: "Zero input: polarity is unscored.",
};

export function interpolate(time, values, at) {
  if (!Number.isFinite(at) || at < time[0] || at > time.at(-1)) {
    throw new RangeError("The requested time is outside the recorded waveform");
  }
  let low = 0;
  let high = time.length - 1;
  while (high - low > 1) {
    const middle = Math.floor((low + high) / 2);
    if (time[middle] <= at) low = middle;
    else high = middle;
  }
  if (at === time[low]) return values[low];
  const fraction = (at - time[low]) / (time[high] - time[low]);
  return values[low] + fraction * (values[high] - values[low]);
}

export function classify(qp, qn, vdd, differential) {
  if (![qp, qn, vdd, differential].every(Number.isFinite) || vdd <= 0) {
    throw new TypeError("Decision inputs must be finite, with a positive supply");
  }
  const decision = qp >= 0.8 * vdd && qn <= 0.2 * vdd ? 1
    : qn >= 0.8 * vdd && qp <= 0.2 * vdd ? -1 : 0;
  const outcome = decision === 0 ? "unresolved" : differential === 0 ? "reference"
    : decision === Math.sign(differential) ? "correct" : "wrong";
  return { decision, outcome };
}

export function inspectSample(data, sampleId, deadline) {
  if (!data.deadlines_ns.includes(deadline)) throw new RangeError("Select a recorded decision deadline");
  const matches = data.samples.filter(sample => sample.id === sampleId);
  if (matches.length !== 1) throw new Error("Unknown or duplicated teaching waveform");
  const sample = matches[0];
  const readings = sample.observations.filter(item => item.deadline_ns === deadline);
  if (readings.length !== 1) throw new Error("A recorded deadline observation is missing or duplicated");
  const reading = readings[0];
  const qp = interpolate(sample.plot.time_ns, sample.plot.qp_v, deadline);
  const qn = interpolate(sample.plot.time_ns, sample.plot.qn_v, deadline);
  if (Math.abs(qp - reading.qp_at_deadline_v) > 1e-9 || Math.abs(qn - reading.qn_at_deadline_v) > 1e-9) {
    throw new Error("The cursor voltages disagree with the measured full-resolution trace");
  }
  const observed = classify(qp, qn, sample.point.vdd_v, sample.point.differential_v);
  if (observed.decision !== reading.decision || observed.outcome !== reading.outcome) {
    throw new Error("Recorded outcome disagrees with the complementary-rail decision contract");
  }
  return { sample, reading, qp, qn, ...observed };
}

export function validateLab(data) {
  if (data.schema !== 1 || data.new_physical_simulations !== 0) throw new Error("Unknown waveform lab schema");
  if (!Array.isArray(data.samples) || data.samples.length !== data.sample_count || !data.samples.length) {
    throw new Error("The teaching waveform set is incomplete");
  }
  if (!Array.isArray(data.deadlines_ns) || !data.deadlines_ns.length
    || data.deadlines_ns.some((value, i, all) => !Number.isFinite(value) || value <= 0 || value > 2
      || (i > 0 && value <= all[i - 1]))) throw new Error("Invalid or unsupported teaching deadlines");
  if (data.rail_thresholds_vdd?.high !== 0.8 || data.rail_thresholds_vdd?.low !== 0.2) {
    throw new Error("The teaching view must not change the published rail thresholds");
  }
  const identifiers = new Set();
  for (const sample of data.samples) {
    if (typeof sample.id !== "string" || identifiers.has(sample.id)) throw new Error("Invalid sample identifier");
    identifiers.add(sample.id);
    if (typeof sample.label !== "string" || typeof sample.description !== "string"
      || !["schematic", "layout_rc"].includes(sample.source_kind)) throw new TypeError("Missing sample scope");
    if (!Number.isFinite(sample.point?.vdd_v) || sample.point.vdd_v <= 0
      || !Number.isFinite(sample.point.differential_v)) throw new TypeError("Invalid physical sample point");
    const time = sample.plot?.time_ns;
    if (!Array.isArray(time) || time.length < 10 || time.some((value, i) => !Number.isFinite(value)
      || (i > 0 && value <= time[i - 1]))) throw new Error("Waveform time must be finite and strictly increasing");
    for (const key of ["qp_v", "qn_v", "clock_v"]) {
      const values = sample.plot[key];
      if (!Array.isArray(values) || values.length !== time.length || !values.every(Number.isFinite)) {
        throw new Error("Waveform vectors are missing, unequal or non-finite");
      }
    }
    if (sample.observations.length !== data.deadlines_ns.length) throw new Error("Incomplete deadline evidence");
    for (const deadline of data.deadlines_ns) {
      const { reading } = inspectSample(data, sample.id, deadline);
      if (reading.reset_ok !== true || !Number.isFinite(reading.core_energy_fj) || reading.core_energy_fj <= 0) {
        throw new Error("The teaching trace lacks a valid reset or measured full-cycle energy");
      }
      if (reading.decision === 0) {
        if (reading.decision_time_ns !== null) throw new Error("An unresolved point has an invented latency");
      } else if (!Number.isFinite(reading.decision_time_ns)
        || reading.decision_time_ns < 0 || reading.decision_time_ns > deadline + 1e-10) {
        throw new Error("The measured decision time is invalid for this deadline");
      }
    }
  }
  return data;
}

function svgElement(document, tag, attributes = {}, text) {
  const element = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  if (text !== undefined) element.textContent = text;
  return element;
}

function renderPlot(document, container, data, result) {
  const { sample, reading } = result;
  const width = Math.max(300, Math.min(1100, Math.round(container.clientWidth || 850)));
  const height = 340;
  const left = 58, right = width - 18, top = 28, bottom = height - 55;
  const [start, end] = data.plot_window_ns;
  const upper = Math.max(sample.point.vdd_v * 1.05, ...sample.plot.qp_v, ...sample.plot.qn_v, ...sample.plot.clock_v) * 1.03;
  const lower = Math.min(-0.03 * sample.point.vdd_v, ...sample.plot.qp_v, ...sample.plot.qn_v);
  const x = time => left + (time - start) / (end - start) * (right - left);
  const y = value => bottom - (value - lower) / (upper - lower) * (bottom - top);
  const svg = svgElement(document, "svg", { viewBox: `0 0 ${width} ${height}`, role: "img",
    "aria-labelledby": "waveform-svg-title waveform-svg-description" });
  svg.append(svgElement(document, "title", { id: "waveform-svg-title" }, sample.label));
  svg.append(svgElement(document, "desc", { id: "waveform-svg-description" },
    `Recorded Q+ and Q- voltages with clock, fixed 80% and 20% supply thresholds and a ${reading.deadline_ns} ns cursor. ${OUTCOME_TEXT[reading.outcome]}`));
  const definitions = svgElement(document, "defs");
  const clip = svgElement(document, "clipPath", { id: "waveform-clip" });
  clip.append(svgElement(document, "rect", { x: left, y: top, width: right - left, height: bottom - top }));
  definitions.append(clip); svg.append(definitions);
  for (const time of [0, 0.5, 1, 1.5, 2]) {
    svg.append(svgElement(document, "line", { x1: x(time), x2: x(time), y1: top, y2: bottom,
      stroke: "#e4eaf1", "stroke-width": 1 }));
    svg.append(svgElement(document, "text", { x: x(time), y: bottom + 23, "text-anchor": "middle",
      fill: "#63758b", "font-size": 12 }, `${time}`));
  }
  for (const fraction of [0, 0.2, 0.5, 0.8, 1]) {
    const value = fraction * sample.point.vdd_v;
    const threshold = fraction === 0.2 || fraction === 0.8;
    svg.append(svgElement(document, "line", { x1: left, x2: right, y1: y(value), y2: y(value),
      stroke: threshold ? "#7889a0" : "#edf1f6", "stroke-dasharray": threshold ? "4 4" : "none" }));
    svg.append(svgElement(document, "text", { x: left - 8, y: y(value) + 4, "text-anchor": "end",
      fill: "#63758b", "font-size": 11 }, value.toFixed(2)));
  }
  const curves = svgElement(document, "g", { "clip-path": "url(#waveform-clip)" });
  for (const [key, color, opacity] of [["clock_v", "#98a8bb", 0.65], ["qp_v", "#009c8d", 1], ["qn_v", "#cc5967", 1]]) {
    const path = sample.plot.time_ns.map((time, i) =>
      `${i ? "L" : "M"}${x(time).toFixed(3)},${y(sample.plot[key][i]).toFixed(3)}`).join(" ");
    curves.append(svgElement(document, "path", { d: path, fill: "none", stroke: color, opacity,
      "stroke-width": key === "clock_v" ? 1.4 : 2.2 }));
  }
  svg.append(curves);
  const cursor = x(reading.deadline_ns);
  svg.append(svgElement(document, "line", { x1: cursor, x2: cursor, y1: top, y2: bottom,
    stroke: "#bb7c21", "stroke-width": 2, "stroke-dasharray": "6 4", "data-deadline": reading.deadline_ns }));
  for (const [value, color] of [[result.qp, "#009c8d"], [result.qn, "#cc5967"]]) {
    svg.append(svgElement(document, "circle", { cx: cursor, cy: y(value), r: 4.5, fill: color, stroke: "white" }));
  }
  svg.append(svgElement(document, "text", { x: left, y: 16, fill: "#63758b", "font-size": 12 }, "Output voltage (V)"));
  svg.append(svgElement(document, "text", { x: (left + right) / 2, y: height - 7,
    "text-anchor": "middle", fill: "#63758b", "font-size": 12 }, "Time after evaluation clock midpoint (ns)"));
  container.replaceChildren(svg);
}

export function mountWaveformLab(document, data) {
  validateLab(data);
  const ids = ["sample", "deadline", "deadline-value", "status", "scope", "rails", "energy",
    "latency", "source", "plot", "error"];
  const controls = Object.fromEntries(ids.map(id => [id, document.getElementById(`waveform-${id}`)]));
  if (Object.values(controls).some(element => !element)) throw new Error("Waveform teaching controls are incomplete");
  for (const sample of data.samples) {
    const option = document.createElement("option");
    option.value = sample.id; option.textContent = sample.label;
    controls.sample.append(option);
  }
  controls.sample.value = data.samples[0].id;
  controls.deadline.min = "0"; controls.deadline.max = String(data.deadlines_ns.length - 1);
  controls.deadline.step = "1"; controls.deadline.value = String(data.deadlines_ns.indexOf(1));

  function render() {
    controls.error.textContent = "";
    try {
      const deadline = data.deadlines_ns[Number(controls.deadline.value)];
      const result = inspectSample(data, controls.sample.value, deadline);
      const { sample, reading } = result;
      const point = sample.point;
      controls["deadline-value"].textContent = `${deadline} ns`;
      controls.deadline.setAttribute("aria-valuetext", `${deadline} ns decision deadline`);
      controls.status.textContent = OUTCOME_TEXT[reading.outcome];
      controls.status.dataset.outcome = reading.outcome;
      controls.scope.textContent = sample.description;
      const required = point.differential_v < 0 ? "Q- high and Q+ low"
        : point.differential_v > 0 ? "Q+ high and Q- low" : "zero input is unscored";
      controls.rails.textContent = `Input ${(point.differential_v * 1000).toFixed(3)} mV requires ${required}. `
        + `High >= ${(0.8 * point.vdd_v).toFixed(3)} V; low <= ${(0.2 * point.vdd_v).toFixed(3)} V. `
        + `At the cursor: Q+ = ${result.qp.toFixed(4)} V, Q- = ${result.qn.toFixed(4)} V.`;
      controls.energy.textContent = `${reading.core_energy_fj.toFixed(2)} fJ / full 10 ns cycle`;
      controls.latency.textContent = reading.decision_time_ns === null
        ? "No rail-valid decision by this deadline"
        : `${reading.decision_time_ns.toFixed(4)} ns sampled decision time (not an exact crossing)`;
      controls.source.textContent = `${sample.source_kind} | ${point.design_name} | trim ${point.trim_code}`
        + ` | run ${sample.run_id} | source waveform SHA256 ${sample.waveform_sha256}`;
      renderPlot(document, controls.plot, data, result);
    } catch (error) {
      controls.error.textContent = `Waveform evidence error: ${error.message}`;
      controls.plot.replaceChildren();
      throw error;
    }
  }
  controls.sample.addEventListener("change", render);
  controls.deadline.addEventListener("input", render);
  controls.deadline.addEventListener("change", render);
  for (const button of document.querySelectorAll("[data-waveform-example]")) {
    button.addEventListener("click", () => {
      controls.sample.value = button.dataset.waveformExample;
      controls.deadline.value = String(data.deadlines_ns.indexOf(Number(button.dataset.waveformDeadline)));
      render();
    });
  }
  document.defaultView?.addEventListener("resize", render);
  render();
  document.defaultView.atlasWaveformLab = {
    show(sampleId, deadline) {
      inspectSample(data, sampleId, deadline);
      controls.sample.value = sampleId;
      controls.deadline.value = String(data.deadlines_ns.indexOf(deadline));
      render();
      controls.sample.focus();
      document.getElementById("waveform-lab").scrollIntoView({ block: "start" });
    },
  };
}

if (typeof document !== "undefined") {
  const source = document.getElementById("waveform-lab-data");
  if (source) mountWaveformLab(document, JSON.parse(source.textContent));
}
