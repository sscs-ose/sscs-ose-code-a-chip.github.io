export const STATUS = ["Wrong", "Unresolved", "Correct", "Calibration unavailable", "Zero input: unscored"];
const COLORS = ["#df5363", "#e9b44c", "#17a897", "#8876c8", "#d5dee9"];

export function validateCube(cube) {
  for (const key of ["designs", "cases", "policies", "deadlines", "inputs", "rows", "trainingCases"]) {
    if (!Array.isArray(cube[key])) throw new TypeError(`Missing explorer array: ${key}`);
  }
  const expected = cube.designs.length * cube.cases.length * cube.policies.length
    * cube.deadlines.length * cube.inputs.length;
  if (cube.rows.length !== expected) throw new Error("Explorer data does not cover its declared grid");
  const keys = new Set();
  for (const row of cube.rows) {
    if (!Array.isArray(row) || row.length !== 9) throw new TypeError("Invalid explorer row");
    for (const [index, limit] of [cube.designs.length, cube.cases.length, cube.policies.length,
      cube.deadlines.length, cube.inputs.length, STATUS.length].entries()) {
      if (!Number.isInteger(row[index]) || row[index] < 0 || row[index] >= limit) {
        throw new RangeError("Explorer row index is out of range");
      }
    }
    const key = row.slice(0, 5).join(":");
    if (keys.has(key)) throw new Error("Duplicate explorer observation");
    keys.add(key);
  }
  return cube;
}

export function filterRows(cube, state) {
  for (const [value, count] of [
    [state.design, cube.designs.length], [state.policy, cube.policies.length],
    [state.deadline, cube.deadlines.length],
  ]) {
    if (!Number.isInteger(value) || value < 0 || value >= count) throw new RangeError("Invalid explorer selection");
  }
  const training = new Set(cube.trainingCases);
  return cube.rows.filter(row => row[0] === state.design && row[2] === state.policy
    && row[3] === state.deadline && (!state.reservedOnly || !training.has(row[1])));
}

export function summarize(cube, records, minimumInputMv) {
  if (!Number.isFinite(minimumInputMv) || minimumInputMv < 0) throw new RangeError("Invalid input guardband");
  const scored = records.filter(row => cube.inputs[row[4]] !== 0
    && Math.abs(cube.inputs[row[4]]) >= minimumInputMv);
  const correct = scored.filter(row => row[5] === 2).length;
  return {
    total: scored.length,
    correct,
    fraction: scored.length ? correct / scored.length : null,
    unavailable: scored.filter(row => row[5] === 3).length,
  };
}

export function mountExplorer(document, cube) {
  validateCube(cube);
  const design = document.getElementById("explorer-design");
  const policy = document.getElementById("explorer-policy");
  const deadline = document.getElementById("explorer-deadline");
  const guardband = document.getElementById("explorer-guardband");
  const reserved = document.getElementById("explorer-reserved");
  const grid = document.getElementById("explorer-grid");
  const detail = document.getElementById("explorer-detail");
  const stats = document.getElementById("explorer-stats");
  if (![design, policy, deadline, guardband, reserved, grid, detail, stats].every(Boolean)) {
    throw new Error("Explorer controls are missing from the report");
  }
  function populate(element, values, initial) {
    for (const [index, value] of values.entries()) {
      const option = document.createElement("option");
      option.value = index;
      option.textContent = value;
      element.append(option);
    }
    element.value = initial;
  }
  populate(design, cube.designs, cube.designs.indexOf(cube.selectedDesign));
  populate(policy, cube.policyLabels, cube.policies.indexOf("local_boundary"));
  populate(deadline, cube.deadlines.map(value => `${value} ns`), cube.deadlines.indexOf(1));
  const guardbands = [0.25, 0.5, 1, 3, 10, 30];
  populate(guardband, guardbands.map(value => `|input| >= ${value} mV`), 2);

  function update() {
    const state = {
      design: Number(design.value), policy: Number(policy.value), deadline: Number(deadline.value),
      reservedOnly: reserved.checked,
    };
    const records = filterRows(cube, state);
    const minimum = guardbands[Number(guardband.value)];
    const score = summarize(cube, records, minimum);
    stats.textContent = `${score.correct} / ${score.total} correct`
      + (score.fraction === null ? "" : ` (${(100 * score.fraction).toFixed(1)}%)`)
      + `; ${score.unavailable} calibration-unavailable points. This is grid coverage, not yield.`;
    detail.textContent = "Select a cell to inspect its recorded condition and measurements.";
    const table = document.createElement("table");
    table.className = "decision-grid";
    const head = document.createElement("thead");
    const header = document.createElement("tr");
    for (const value of ["Operating condition", ...cube.inputs.map(value => `${value} mV`)]) {
      const cell = document.createElement("th");
      cell.textContent = value;
      header.append(cell);
    }
    head.append(header);
    table.append(head);
    const body = document.createElement("tbody");
    const cells = new Map(records.map(row => [`${row[1]}:${row[4]}`, row]));
    const presentCases = [...new Set(records.map(row => row[1]))].sort((a, b) => a - b);
    for (const caseIndex of presentCases) {
      const tr = document.createElement("tr");
      const label = document.createElement("th");
      label.textContent = cube.cases[caseIndex]
        + (cube.trainingCases.includes(caseIndex) ? " [selection]" : "");
      tr.append(label);
      for (let inputIndex = 0; inputIndex < cube.inputs.length; inputIndex++) {
        const row = cells.get(`${caseIndex}:${inputIndex}`);
        if (!row) throw new Error("Explorer grid has a missing observation");
        const td = document.createElement("td");
        const button = document.createElement("button");
        const input = cube.inputs[inputIndex];
        button.className = "grid-cell";
        button.dataset.caseIndex = String(caseIndex);
        button.dataset.inputIndex = String(inputIndex);
        if (input === 0 || Math.abs(input) < minimum) button.classList.add("outside-score");
        button.style.backgroundColor = COLORS[row[5]];
        button.title = `${cube.cases[caseIndex]}, ${input} mV: ${STATUS[row[5]]}`;
        button.setAttribute("aria-label", button.title);
        button.textContent = row[5] === 3 ? "!" : row[5] === 4 ? "-" : "\u00a0";
        button.addEventListener("click", () => {
          const delay = row[6] === null ? "not resolved / unavailable" : `${row[6]} ns`;
          const energy = row[7] === null ? "not simulated" : `${row[7]} fJ`;
          const code = row[8] === null ? "unavailable" : String(row[8]);
          detail.textContent = `${cube.designs[state.design]} | ${cube.cases[caseIndex]}`
            + ` | input ${input} mV | deadline ${cube.deadlines[state.deadline]} ns`
            + ` | ${STATUS[row[5]]} | trim ${code} | decision time ${delay} | core energy ${energy}.`;
        });
        td.append(button);
        tr.append(td);
      }
      body.append(tr);
    }
    table.append(body);
    grid.replaceChildren(table);
  }
  for (const element of [design, policy, deadline, guardband, reserved]) {
    element.addEventListener("change", update);
  }
  update();
  document.defaultView.atlasStoredExplorer = {
    focus(record) {
      const indices = [cube.designs.indexOf(record.design_name), cube.cases.indexOf(record.case_id),
        cube.deadlines.indexOf(record.deadline_ns), cube.inputs.indexOf(record.input_mv)];
      if (indices.some(index => index < 0) || !cube.policies.includes("local_boundary")) {
        throw new Error("The measurement key is outside this stored-decision map");
      }
      design.value = String(indices[0]);
      policy.value = String(cube.policies.indexOf("local_boundary"));
      deadline.value = String(indices[2]);
      reserved.checked = false;
      update();
      const button = grid.querySelector(`[data-case-index="${indices[1]}"][data-input-index="${indices[3]}"]`);
      if (!button) throw new Error("The keyed decision-map cell is missing");
      grid.closest("details").open = true;
      button.click();
      button.focus();
      button.scrollIntoView({ block: "nearest" });
    },
  };
}

if (typeof document !== "undefined") {
  const source = document.getElementById("atlas-cube");
  if (source) mountExplorer(document, JSON.parse(source.textContent));
}
