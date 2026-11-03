/** Original HuLLCirq symbols: stage identity is independent of status colour. */
import { svgElement as svg } from './dom.js';

const p = d => ['path', { d }];
const r = (x, y, width, height, rx = 0) => ['rect', { x, y, width, height, rx }];
const c = (cx, cy, radius) => ['circle', { cx, cy, r: radius }];

const STAGE_SHAPES = Object.freeze({
  global_settings: [p('M4 6h5m4 0h7M4 12h9m4 0h3M4 18h3m4 0h9'), c(11, 6, 2), c(15, 12, 2), c(9, 18, 2)],
  graph_editor: [p('M7 6h9M5 8v8m2 2h9m2-2V8M7 8l9 8'), r(3, 4, 4, 4, 1), r(16, 4, 4, 4, 1), r(3, 16, 4, 4, 1), r(16, 16, 4, 4, 1)],
  specifications: [p('M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8l-5-5Zm0 0v5h5M8 12l1 1 2-2m2 1h3M8 17l1 1 2-2m2 1h3')],
  local_rtl_generation: [p('m7 8-4 4 4 4m4-8 4 4-4 4m8-14 1 3 3 1-3 1-1 3-1-3-3-1 3-1 1-3M4 21h13')],
  local_synthesis: [p('M3 7h5m-5 10h5m8-5h5M8 5h2a7 7 0 0 1 0 14H8V5Z'), c(19, 12, 2)],
  local_netlist_simulation: [p('M3 4v16h18M5 13h3V7h5v10h5v-6h3')],
  node_implementation_specs: [p('M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8l-5-5Zm0 0v5h5M8 11h4M8 15h2m2 2 2 2 5-5')],
  global_rtl_generation: [p('m6 3-3 3 3 3m4-6 3 3-3 3M8 11v3m-4 3v-3h14v3'), r(2, 17, 5, 4, 1), r(9, 17, 5, 4, 1), r(16, 17, 5, 4, 1)],
  global_synthesis: [r(6, 6, 12, 12, 2), r(9, 9, 6, 6, 1), p('M9 3v3m6-3v3M9 18v3m6-3v3M3 9h3m-3 6h3m12-6h3m-3 6h3')],
  global_netlist_simulation: [p('M3 3v18h18M5 8h3V5h5v6h4V8h4M5 17h5v-4h5v6h3v-4h3')],
  layout: [p('m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5')],
  drc: [p('M4 3h8v7M7 3v3m3-3v3M4 7h3M4 3v18h5M4 11h3m-3 4h3m7-6 6 3v5c0 2-3 4-6 5-3-1-6-3-6-5v-5l6-3Zm-3 7 2 2 4-4')],
  lvs: [p('M3 5h5v5h3M3 19h5v-5h3m2-4h3V5h5m-8 9h3v5h5M10 12h4'), c(3, 5, 1), c(3, 19, 1), c(21, 5, 1), c(21, 19, 1)],
  post_layout_verification: [c(12, 13, 8), p('M10 2h4m-2 0v3m5 2 2-2M5 13h3l2-4 3 8 2-4h4')],
});

const STATUS_SHAPES = Object.freeze({
  complete: [c(12, 12, 9), p('m7 12 3 3 7-7')],
  working: [p('M20 12a8 8 0 1 1-3-6M20 4v5h-5')],
  attention: [p('M12 3 2 21h20L12 3Zm0 6v5m0 3v.5')],
  error: [c(12, 12, 9), p('m9 9 6 6m0-6-6 6')],
  blocked: [r(5, 10, 14, 11, 2), p('M8 10V7a4 4 0 0 1 8 0v3m-4 4v3')],
  pending: [c(12, 12, 8)],
});

function draw(shapes, className, identity) {
  return svg('svg', { viewBox: '0 0 24 24', width: 24, height: 24, fill: 'none', stroke: 'currentColor',
    'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round',
    'aria-hidden': 'true', focusable: 'false', class: className, 'data-icon': identity },
  shapes.map(([tag, attributes]) => svg(tag, attributes)));
}

export function stageIcon(stageId, { class: className = 'stage-icon' } = {}) {
  return draw(STAGE_SHAPES[stageId] || STATUS_SHAPES.pending, className, stageId || 'unknown-stage');
}

export function statusIcon(stateKind, { class: className = 'status-icon' } = {}) {
  return draw(STATUS_SHAPES[stateKind] || STATUS_SHAPES.pending, className, stateKind || 'pending');
}
