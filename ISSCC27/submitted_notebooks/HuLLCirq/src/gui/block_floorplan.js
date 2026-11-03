import { element as el, svgElement, field, badge } from './dom.js';
import { placementTargets, targetValue, parseTarget } from './design_instances.js';

const VERSION = 'block-regions-v1';
const TILE_INSET_UM = 6;
const DEFAULT_SUPPORT_SPACING_UM = 24;
const GRID_TICKS_PER_UM = 200; // One manufacturing-grid tick is exactly 0.005 µm.
const GRID_FLOAT_TOLERANCE_TICKS = 1e-7;
const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
const validRect = rect => Array.isArray(rect) && rect.length === 4 && rect.every(value => typeof value === 'number' && Number.isFinite(value)) && rect[2] > rect[0] && rect[3] > rect[1];
const onGrid = value => typeof value === 'number' && Number.isFinite(value)
  && Math.abs(value * GRID_TICKS_PER_UM - Math.round(value * GRID_TICKS_PER_UM)) < GRID_FLOAT_TOLERANCE_TICKS;
const gridRect = rect => validRect(rect) && rect.every(onGrid);
const overlaps = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
const supportSpacingProblem = value => typeof value !== 'number' || !Number.isFinite(value)
  ? 'Enter a finite support spacing in micrometres.'
  : value < TILE_INSET_UM ? 'New tiling support spacing must be at least 6 µm.'
    : !onGrid(value) ? 'New tiling support spacing must lie on the 0.005 µm manufacturing grid. It is not rounded.' : '';

/** Draft validation only. Authoritative source/placement checks run in the backend. */
export function validateFloorplan(design) {
  const plan = design.physical_design;
  if (!plan || plan.version === 'mixed-v1') return [];
  const problems = [], choices = new Map(placementTargets(design)), assigned = new Set(), ids = new Set();
  if (plan.version !== VERSION) problems.push('Unsupported block floorplan version.');
  if (!validRect(plan.core_um)) problems.push('Core coordinates must be finite and define a positive-area rectangle.');
  else if (plan.core_um[0] < 10 || plan.core_um[1] < 10) problems.push('Core X min and Y min must be at least 10 µm to leave room for die margins.');
  if (validRect(plan.core_um) && (plan.core_um[2] - plan.core_um[0] <= TILE_INSET_UM * 2 || plan.core_um[3] - plan.core_um[1] <= TILE_INSET_UM * 2)) problems.push('Core width and height must be greater than 12 µm. This retains the minimum 6 µm legacy spacing; new tiling can require more room for its chosen support spacing.');
  if (validRect(plan.core_um) && !gridRect(plan.core_um)) problems.push('Every core coordinate must lie on the 0.005 µm manufacturing grid. Manual coordinates are not rounded.');
  if (!Array.isArray(plan.regions) || !plan.regions.length) problems.push('Assign every physical instance to a region.');
  for (const region of plan.regions || []) {
    if (typeof region.id !== 'string' || !/^[A-Za-z_][A-Za-z0-9_-]*$/.test(region.id) || ids.has(region.id)) problems.push('Region IDs must be unique identifiers.');
    ids.add(region.id);
    if (!validRect(region.rect_um)) problems.push(`${region.id}: use a finite positive-area rectangle.`);
    else if (validRect(plan.core_um) && (region.rect_um[0] < plan.core_um[0] || region.rect_um[1] < plan.core_um[1] || region.rect_um[2] > plan.core_um[2] || region.rect_um[3] > plan.core_um[3])) problems.push(`${region.id}: the region must stay inside the core.`);
    if (validRect(region.rect_um) && !gridRect(region.rect_um)) problems.push(`${region.id}: every coordinate must lie on the 0.005 µm manufacturing grid. Manual coordinates are not rounded.`);
    if (!Array.isArray(region.targets) || !region.targets.length) problems.push(`${region.id}: select at least one physical instance.`);
    for (const target of region.targets || []) {
      const key = targetValue(target);
      if (!choices.has(key)) problems.push(`${region.id}: an instance target no longer exists.`);
      if (assigned.has(key)) problems.push(`${region.id}: a physical instance is assigned more than once.`);
      assigned.add(key);
    }
  }
  for (let i = 0; i < (plan.regions || []).length; i++) for (let j = i + 1; j < plan.regions.length; j++)
    if (validRect(plan.regions[i].rect_um) && validRect(plan.regions[j].rect_um) && overlaps(plan.regions[i].rect_um, plan.regions[j].rect_um)) problems.push(`${plan.regions[i].id} / ${plan.regions[j].id}: regions overlap.`);
  const missing = [...choices].filter(([key]) => !assigned.has(key)).map(([, label]) => label);
  if (missing.length) problems.push(`Unassigned instances: ${missing.join(', ')}.`);
  return problems;
}

export function tiledRegions(design, core, supportSpacingUm = DEFAULT_SUPPORT_SPACING_UM) {
  const targets = placementTargets(design);
  if (!gridRect(core) || !targets.length || supportSpacingProblem(supportSpacingUm)) return [];
  const columns = Math.ceil(Math.sqrt(targets.length)), rows = Math.ceil(targets.length / columns);
  // Only an explicitly requested generated draft is quantized. Accepted core
  // coordinates are converted to integer ticks within representation tolerance;
  // entered manual rectangles are never changed by validation or preview.
  const ticks = core.map(value => Math.round(value * GRID_TICKS_PER_UM));
  const inset = Math.round(supportSpacingUm * GRID_TICKS_PER_UM), gap = inset;
  const innerWidth = ticks[2] - ticks[0] - inset * 2, innerHeight = ticks[3] - ticks[1] - inset * 2;
  const cellWidth = Math.floor((innerWidth - gap * (columns - 1)) / columns), cellHeight = Math.floor((innerHeight - gap * (rows - 1)) / rows);
  if (innerWidth <= 0 || innerHeight <= 0 || cellWidth <= 0 || cellHeight <= 0) return [];
  const sharedArray = design.nodes.find(node => node.instance_array?.rows === 2 && node.instance_array?.columns === 2);
  const reserved = new Map();
  if (sharedArray && columns >= 2 && rows >= 2) for (const [key] of targets) {
    const target = parseTarget(key), index = target.instance_index;
    if (target.node_id === sharedArray.id && Array.isArray(index)) reserved.set(key, (rows - 1 - index[0]) * columns + index[1]);
  }
  const reservedSlots = new Set(reserved.values()), remaining = Array.from({ length: rows * columns }, (_, index) => index).filter(index => !reservedSlots.has(index));
  return targets.map(([key], index) => {
    const slot = reserved.has(key) ? reserved.get(key) : remaining.shift();
    const column = slot % columns, row = Math.floor(slot / columns);
    const x = ticks[0] + inset + (cellWidth + gap) * column, y = ticks[1] + inset + (cellHeight + gap) * row;
    return { id: `region_${index + 1}`, targets: [parseTarget(key)], rect_um: [
      x, y, x + cellWidth, y + cellHeight,
    ].map(value => value / GRID_TICKS_PER_UM) };
  });
}

/** Browser-only editing. Only the explicit Save design callback writes project files. */
export class BlockFloorplan {
  constructor(callbacks) { this.callbacks = callbacks; this.supportSpacingRaw = String(DEFAULT_SUPPORT_SPACING_UM); }
  project() { return this.callbacks.project(); }
  supportSpacing() { return this.supportSpacingRaw.trim() === '' ? NaN : Number(this.supportSpacingRaw); }
  refreshTilingHelper() {
    if (!this.tilingNote) return;
    const spacing = this.supportSpacing(), problem = supportSpacingProblem(spacing);
    this.tilingNote.textContent = problem || `The next explicit Tile uses ${spacing} µm for both the outer inset and support-channel gaps. This helper is not part of the saved plan; existing rectangles are unchanged until Tile. Spacing is not a support-capacity or legalization proof.`;
  }
  change(callback, rebuild = false) {
    this.callbacks.mutate(callback);
    if (rebuild) this.render(this.host); else this.preview();
  }
  render(host) {
    this.host = host;
    this.tilingNote = null;
    const p = this.project(), plan = p.design.physical_design, blockMode = !!plan && plan.version !== 'mixed-v1', targets = placementTargets(p.design);
    let selectedMode = blockMode ? 'regions' : 'mixed';
    const mode = field('Placement mode', selectedMode, value => { selectedMode = value; }, {
      id: 'block-placement-mode', 'data-testid': 'block-placement-mode',
      choices: [['mixed', 'Mixed placement (existing flow)'], ['regions', 'Block regions (one chip)']],
    });
    const controls = el('fieldset', { class: 'block-floorplan-fields', disabled: p.readOnly || p.busy || !!p.conflict }, mode,
      el('button', { type: 'button', text: 'Apply placement mode to draft', 'data-testid': 'apply-placement-mode', onclick: () => this.change(design => {
        if (selectedMode === 'mixed') design.physical_design = { version: 'mixed-v1' };
        else if (!design.physical_design || design.physical_design.version === 'mixed-v1') design.physical_design = { version: VERSION, core_um: [10, 10, 1010, 1010], regions: [] };
      }, true) }));
    if (blockMode) {
      this.tilingNote = el('p', { class: 'scope-note', role: 'status', 'data-testid': 'block-tiling-support-note' });
      controls.append(
      el('h3', { text: 'Core rectangle (µm · 0.005 µm grid)' }), this.rectFields(plan.core_um, 'core', (index, value) => this.change(design => { design.physical_design.core_um[index] = value; })),
      field('New tiling support spacing (µm)', this.supportSpacingRaw, value => {
        this.supportSpacingRaw = value; this.refreshTilingHelper();
      }, { id: 'block-tiling-support-spacing', type: 'number', min: '6', step: '0.005', 'data-testid': 'block-tiling-support-spacing', hint: 'Browser-only helper for the next explicit Tile. Changing this value does not edit, save or run the design.' }),
      this.tilingNote,
      el('div', { class: 'provider-actions' },
        el('button', { type: 'button', text: 'Tile on 0.005 µm grid', 'data-testid': 'tile-block-regions', onclick: () => {
          const spacing = this.supportSpacing(), problem = supportSpacingProblem(spacing);
          if (problem) { this.callbacks.notify?.(`${problem} Existing draft regions were not changed.`, 'warning'); return; }
          const current = this.project().design, regions = tiledRegions(current, current.physical_design.core_um, spacing);
          if (!gridRect(current.physical_design.core_um)) { this.callbacks.notify?.('Core coordinates must lie on the 0.005 µm manufacturing grid before tiling. Nothing was rounded; existing draft regions were not changed.', 'warning'); return; }
          if (!regions.length) { this.callbacks.notify?.(`The core is too small for a ${spacing} µm inset and ${spacing} µm gaps. Increase its width and height or explicitly choose a smaller valid helper spacing; existing draft regions were not changed.`, 'warning'); return; }
          this.change(design => { design.physical_design.regions = regions; }, true);
        } }),
        el('button', { type: 'button', text: '+ Add region', 'data-testid': 'add-block-region', onclick: () => this.change(design => {
          const regions = design.physical_design.regions;
          let index = regions.length + 1; while (regions.some(region => region.id === `region_${index}`)) index++;
          regions.push({ id: `region_${index}`, targets: [], rect_um: [...design.physical_design.core_um] });
        }, true) })),
      el('p', { class: 'scope-note', text: 'The explicit tiler uses integer 0.005 µm manufacturing-grid ticks and the chosen support spacing for both the core inset and gaps. Its new default is 24 µm; saved 6 µm plans remain unchanged and readable. Equal tile sizes are rounded down in integer ticks; unused remainder stays at the top and right. A shared 2 × 2 array keeps its arrangement, with row 0 at the top. The exact generated rectangles are shown below. Manual coordinates are never silently rounded, clipped or shifted. Draft geometry does not prove space for inserted clock/support cells or successful placement.' }),
      el('div', { class: 'block-region-list' }, plan.regions.map((region, index) => this.regionFields(region, index, targets))));
      this.refreshTilingHelper();
    }
    this.status = el('div', { class: 'generation-summary', role: 'status', 'aria-live': 'polite', 'data-testid': 'block-floorplan-status' });
    this.previewHost = el('div', { class: 'block-floorplan-preview', 'data-testid': 'block-floorplan-preview' });
    this.saveButton = el('button', { type: 'button', class: 'primary', text: 'Save design', 'data-testid': 'save-block-floorplan', onclick: async () => {
      const problems = validateFloorplan(this.project().design);
      if (problems.length) { this.preview(); return; }
      await this.callbacks.save(); this.render(this.host);
    } });
    host.replaceChildren(el('section', { class: 'card block-floorplan-card' },
      el('div', { class: 'card-heading' }, el('h2', { text: 'Block floorplan' }),
        el('p', { text: 'Assign same-chip placement regions to blocks and indexed PE instances. Mixed placement remains available. These are physical constraints, not Graph Editor drawing coordinates.' })),
      el('p', { class: 'scope-note', text: 'Viewing this tab and editing its draft do not start tools or save project files. Save design explicitly records the selected mode and complete region plan. A saved block plan requires new source-bound physical execution and verified region containment; this drawing is a planning preview, not placed-cell evidence or a Passed result.' }),
      controls, this.status, this.previewHost,
      el('div', { class: 'provider-actions' }, el('button', { type: 'button', text: 'Validate draft preview', 'data-testid': 'validate-block-floorplan', onclick: () => this.preview() }), this.saveButton)));
    this.preview();
  }
  rectFields(rect, prefix, change) {
    return el('div', { class: 'form-grid block-rectangle-fields' }, ...['X min', 'Y min', 'X max', 'Y max'].map((label, index) =>
      field(label, rect[index], value => change(index, value.trim() === '' ? null : Number(value)), { id: `block-${prefix}-${index}`, type: 'number', step: '0.005', 'data-testid': `block-${prefix}-${index}` })));
  }
  regionFields(region, index, targets) {
    const change = callback => this.change(design => callback(design.physical_design.regions[index]));
    const used = new Set(region.targets.map(targetValue));
    let addition = targets.find(([key]) => !used.has(key))?.[0] || '';
    return el('section', { class: 'block-region-fields', 'data-testid': `block-region-${index}` },
      field('Region ID', region.id, value => change(target => { target.id = value; }), { id: `block-region-id-${index}`, 'data-testid': `block-region-id-${index}` }),
      this.rectFields(region.rect_um, `region-${index}`, (coordinate, value) => change(target => { target.rect_um[coordinate] = value; })),
      el('div', { class: 'block-targets' }, region.targets.map((target, targetIndex) => el('div', { class: 'block-target-row' },
        field('Physical instance', targetValue(target), value => { this.change(design => { design.physical_design.regions[index].targets[targetIndex] = parseTarget(value); }, true); }, { id: `block-target-${index}-${targetIndex}`, choices: targets, 'data-testid': `block-target-${index}-${targetIndex}` }),
        el('button', { type: 'button', text: 'Remove target', onclick: () => this.change(design => { design.physical_design.regions[index].targets.splice(targetIndex, 1); }, true) })))),
      field('Additional instance', addition, value => { addition = value; }, { id: `block-add-target-${index}`, choices: targets.filter(([key]) => !used.has(key)), disabled: used.size >= targets.length }),
      el('div', { class: 'provider-actions' }, el('button', { type: 'button', text: 'Add target', disabled: !addition, onclick: () => {
        if (addition) this.change(design => { design.physical_design.regions[index].targets.push(parseTarget(addition)); }, true);
      } }), el('button', { type: 'button', class: 'danger', text: 'Delete region', onclick: () => this.change(design => { design.physical_design.regions.splice(index, 1); }, true) })));
  }
  preview() {
    if (!this.status) return;
    const p = this.project(), plan = p.design.physical_design, blockMode = !!plan && plan.version !== 'mixed-v1', problems = validateFloorplan(p.design);
    const saved = same(plan, p.saved?.physical_design);
    this.status.replaceChildren(badge(saved ? 'Saved placement mode' : 'Unsaved placement draft', saved ? 'teal' : 'orange'),
      el('span', { text: blockMode ? `Block regions · ${plan.regions.length} region(s) · planning preview only` : 'Mixed placement · no fixed block regions' }),
      ...(problems.length ? [el('ul', {}, problems.map(text => el('li', { text })))] : [el('p', { text: blockMode ? 'Draft geometry and instance coverage are valid. Backend placement verification is still required.' : 'Mixed placement is selected. Explicitly saving this mode selects the original mixed-placement profile for new runs.' })]));
    this.saveButton.disabled = p.readOnly || p.busy || !!p.conflict || !p.dirty || !!problems.length;
    this.previewHost.replaceChildren();
    if (!blockMode || !validRect(plan.core_um)) return;
    const core = plan.core_um, width = core[2] - core[0], height = core[3] - core[1], labels = new Map(placementTargets(p.design));
    const svg = svgElement('svg', { viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': 'Block floorplan draft in micrometres; not a placed layout' },
      svgElement('rect', { x: 0, y: 0, width, height, fill: '#f3f6fa', stroke: '#233b66', 'stroke-width': width / 500 }));
    for (const [index, region] of plan.regions.entries()) {
      if (!validRect(region.rect_um)) continue;
      const rect = region.rect_um, x = rect[0] - core[0], y = core[3] - rect[3], w = rect[2] - rect[0], h = rect[3] - rect[1];
      const group = svgElement('g', {}, svgElement('title', { text: `${region.id}: ${region.targets.map(target => labels.get(targetValue(target)) || 'Missing target').join(', ')} · ${rect.join(', ')} µm` }),
        svgElement('rect', { x, y, width: w, height: h, fill: `hsl(${(index * 71) % 360} 50% 85%)`, stroke: '#405779', 'stroke-width': width / 650 }),
        svgElement('text', { x: x + w / 2, y: y + h / 2, 'text-anchor': 'middle', 'dominant-baseline': 'middle', 'font-size': Math.min(width / 45, w / 8, h / 4), fill: '#132a4b', text: region.id }));
      svg.append(group);
    }
    this.previewHost.append(svg, el('small', { text: 'Region planning preview · µm · no cell placement or signoff is implied.' }));
  }
}
