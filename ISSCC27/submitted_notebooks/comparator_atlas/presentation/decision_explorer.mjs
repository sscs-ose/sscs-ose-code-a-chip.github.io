export function selection(data, minimum, deadline) {
  if (!data.minimums.includes(minimum) || !data.deadlines.includes(deadline)) {
    throw new RangeError("Choose a published sampled input and deadline; no interpolation");
  }
  const choices = data.selections.filter(row => row.minimum_abs_input_mv === minimum
    && row.deadline_ns === deadline);
  const candidates = data.candidates.filter(row => row.minimum_abs_input_mv === minimum
    && row.deadline_ns === deadline);
  if (choices.length !== 1 || candidates.length !== 3) throw new Error("Incomplete strict selection");
  const feasible = candidates.filter(row => row.all_correct);
  const minimumEnergy = feasible.length ? Math.min(...feasible.map(row => row.mean_core_energy_fj)) : null;
  const ties = data.designs.filter(design => feasible.some(row => row.design === design
    && row.mean_core_energy_fj === minimumEnergy));
  const choice = choices[0];
  if (choice.winner !== (ties[0] ?? null) || choice.mean_core_energy_fj !== minimumEnergy
    || JSON.stringify(choice.minimum_energy_ties) !== JSON.stringify(ties)) {
    throw new Error("Published strict winner/null/exact tie contract disagrees");
  }
  for (const row of candidates) {
    if (row.correct + row.wrong + row.unresolved !== row.points
      || row.all_correct !== (row.correct === row.points && row.fully_passing_conditions === 49)) {
      throw new Error("Candidate count closure or qualification disagrees");
    }
  }
  return { choice, candidates };
}

export function witnesses(data, minimum, deadline, design) {
  selection(data, minimum, deadline);
  if (!data.designs.includes(design)) throw new RangeError("Unknown compared design");
  return data.observations.filter(row => row.design_name === design && row.deadline_ns === deadline
    && Math.abs(row.input_mv) >= minimum && row.outcome !== "correct");
}

export function mountDecision(document, data) {
  const element = id => {
    const value = document.getElementById(id);
    if (!value) throw new Error(`Missing integrated decision control: ${id}`);
    return value;
  };
  const minimum = element("explorer-guardband"), deadline = element("explorer-deadline");
  const design = element("explorer-design"), result = element("decision-result");
  const candidates = element("decision-candidates"), records = element("decision-records");
  const pageLabel = element("decision-page"), next = element("decision-next");
  const previous = element("decision-previous"), error = element("decision-error");
  let currentMinimum = 1, currentDeadline = 1, page = 0, activeKey = "";

  function renderRecords() {
    const name = data.designs[Number(design.value)];
    const rows = witnesses(data, currentMinimum, currentDeadline, name);
    const count = 12, start = page * count;
    pageLabel.textContent = `${name}: ${rows.length} exact disqualifying measurements. `
      + (rows.length ? `Showing ${start + 1}-${Math.min(start + count, rows.length)}.` : "No disqualifying key in this band.");
    previous.disabled = page === 0;
    next.disabled = start + count >= rows.length;
    const list = document.createElement("ol");
    for (const record of rows.slice(start, start + count)) {
      const item = document.createElement("li");
      item.className = "measurement-record";
      item.dataset.observationId = String(record.observation_id);
      const title = document.createElement("strong");
      title.textContent = `${record.outcome.toUpperCase()} | ${record.case_id} | ${record.input_mv > 0 ? "+" : ""}${record.input_mv} mV | ${record.deadline_ns} ns`;
      const values = document.createElement("p");
      values.textContent = `${record.corner.toUpperCase()} / ${record.vdd_v} V / ${record.temperature_c} C`
        + ` / width stress ${record.pair_skew} / trim ${record.trim_code}; `
        + `decision time ${record.decision_time_ns === null ? "null (unresolved)" : record.decision_time_ns + " ns"}; `
        + `full-cycle core energy ${record.core_energy_fj.toFixed(6)} fJ.`;
      const identity = document.createElement("code");
      identity.textContent = `run ${record.run_id} | CSV record ${record.source_record}`;
      const link = document.createElement("a");
      link.href = record.source_csv;
      link.textContent = "Open exact source measurement table";
      const map = document.createElement("button");
      map.type = "button"; map.textContent = "Inspect this key in the stored map";
      map.addEventListener("click", () => document.defaultView.atlasStoredExplorer.focus(record));
      const wave = document.createElement(record.waveform_sample_id === null ? "p" : "button");
      if (record.waveform_sample_id === null) {
        wave.textContent = "No matching retained raw waveform for this key: measurement record only.";
        wave.className = "muted";
      } else {
        wave.type = "button"; wave.textContent = "Open the identity-matched retained waveform";
        wave.addEventListener("click", () => document.defaultView.atlasWaveformLab.show(
          record.waveform_sample_id, record.deadline_ns));
      }
      item.append(title, values, identity, document.createElement("br"), link, map, wave);
      list.append(item);
    }
    records.replaceChildren(list);
  }

  function update() {
    error.textContent = "";
    try {
      currentMinimum = data.minimums[Number(minimum.value)];
      currentDeadline = data.deadlines[Number(deadline.value)];
      const { choice, candidates: rows } = selection(data, currentMinimum, currentDeadline);
      const key = `${currentMinimum}:${currentDeadline}`;
      result.textContent = choice.winner === null
        ? `NONE - no feasible compared design at sampled |input| >= ${currentMinimum} mV, ${currentDeadline} ns. Winner energy and limits: null.`
        : `${choice.winner} | ${choice.mean_core_energy_fj.toFixed(3)} fJ mean core / cycle `
          + `| all included points correct at ${currentDeadline} ns. Exact minimum-energy ties: ${choice.minimum_energy_ties.join(", ")}.`;
      result.dataset.winner = choice.winner ?? "NONE";
      const table = document.createElement("table");
      const head = document.createElement("thead");
      const header = document.createElement("tr");
      for (const label of ["Compared design", "Correct", "Wrong", "Unresolved", "Points", "All 49 qualify?", "Mean core fJ", "Inspect records"]) {
        const th = document.createElement("th"); th.textContent = label; header.append(th);
      }
      head.append(header); table.append(head);
      const body = document.createElement("tbody");
      for (const row of rows) {
        const tr = document.createElement("tr");
        for (const value of [row.design, row.correct, row.wrong, row.unresolved, row.points,
          row.all_correct ? "YES" : "NO", row.mean_core_energy_fj.toFixed(3)]) {
          const td = document.createElement("td"); td.textContent = String(value); tr.append(td);
        }
        const td = document.createElement("td"), button = document.createElement("button");
        button.type = "button"; button.textContent = row.all_correct ? "Qualified" : `${row.wrong + row.unresolved} keys`;
        button.setAttribute("aria-label", `Inspect ${row.design} measurement keys`);
        button.addEventListener("click", () => {
          design.value = String(data.designs.indexOf(row.design));
          design.dispatchEvent(new document.defaultView.Event("change"));
        });
        td.append(button); tr.append(td); body.append(tr);
      }
      table.append(body); candidates.replaceChildren(table);
      if (activeKey !== key) {
        activeKey = key;
        design.value = String(data.designs.indexOf(choice.winner ?? "lvt_balanced_4b"));
        design.dispatchEvent(new document.defaultView.Event("change"));
      }
      page = 0;
      renderRecords();
    } catch (failure) {
      result.textContent = "No recommendation: evidence/state error.";
      candidates.replaceChildren(); records.replaceChildren();
      error.textContent = failure.message;
      throw failure;
    }
  }
  for (const control of [minimum, deadline]) control.addEventListener("change", update);
  design.addEventListener("change", () => { page = 0; renderRecords(); });
  previous.addEventListener("click", () => { page--; renderRecords(); });
  next.addEventListener("click", () => { page++; renderRecords(); });
  for (const button of document.querySelectorAll("[data-decision-preset]")) {
    button.addEventListener("click", () => {
      minimum.value = String(data.minimums.indexOf(Number(button.dataset.decisionPreset)));
      deadline.value = String(data.deadlines.indexOf(1));
      // Notify the reused map only after both specification controls hold their new values.
      minimum.dispatchEvent(new document.defaultView.Event("change"));
    });
  }
  document.defaultView.atlasDecision = { data, selection, witnesses };
  function applyKeyLink() {
    const fragment = document.defaultView.location.hash;
    if (!fragment.startsWith("#decision=")) return;
    try {
      const [band, time, index] = fragment.slice(10).split(",").map(Number);
      selection(data, band, time);
      const record = data.observations[index];
      if (!Number.isInteger(index) || !record || record.observation_id !== index
        || record.deadline_ns !== time || Math.abs(record.input_mv) < band) {
        throw new Error("Invalid keyed observation link");
      }
      minimum.value = String(data.minimums.indexOf(band));
      deadline.value = String(data.deadlines.indexOf(time));
      minimum.dispatchEvent(new document.defaultView.Event("change"));
      design.value = String(data.designs.indexOf(record.design_name));
      design.dispatchEvent(new document.defaultView.Event("change"));
      const failures = witnesses(data, currentMinimum, currentDeadline, record.design_name);
      const position = failures.findIndex(row => row.observation_id === record.observation_id);
      if (position >= 0) {
        page = Math.floor(position / 12);
        renderRecords();
      }
      document.defaultView.atlasStoredExplorer.focus(record);
    } catch (failure) {
      result.textContent = "No recommendation: invalid evidence link.";
      error.textContent = failure.message;
      candidates.replaceChildren(); records.replaceChildren();
      throw failure;
    }
  }
  document.defaultView.addEventListener("hashchange", applyKeyLink);
  update();
  applyKeyLink();
}

if (typeof document !== "undefined") {
  const source = document.getElementById("atlas-decision-data");
  if (source) mountDecision(document, JSON.parse(source.textContent));
}
