import { element, svgElement } from './dom.js';
import { arrayShape, instanceIndices, instanceSuffix } from './design_instances.js';
import { hasExternalIO, externalBlocks, externalBindingLabel } from './external_io.js';

const NODE_WIDTH = 228;
const PORT_ROW = 28;
const displayPorts = node => instanceIndices(node).flatMap(instance_index => node.ports.map(port => ({ ...port, instance_index })));
const headerHeight = node => arrayShape(node) ? 85 : 63;
const nodeHeight = node => headerHeight(node) + 15 + Math.max(1, ...['input', 'output'].map(direction => displayPorts(node).filter(port => port.direction === direction).length)) * PORT_ROW;
const position = (design, nodeId) => Object.hasOwn(design.layout.nodes, nodeId) ? design.layout.nodes[nodeId] : { x: 80, y: 80 };
const portOffset = (node, portId, index) => {
  const port = node.ports.find(item => item.id === portId);
  if (!port) return { x: NODE_WIDTH / 2, y: nodeHeight(node) / 2 };
  const siblings = displayPorts(node).filter(item => item.direction === port.direction);
  const row = siblings.findIndex(item => item.id === portId && instanceSuffix(item.instance_index) === instanceSuffix(index));
  return { x: port.direction === 'output' ? NODE_WIDTH : 0, y: headerHeight(node) + 20 + Math.max(0, row) * PORT_ROW };
};

/** A semantic graph; drawing coordinates are isolated in design.layout. */
export class GraphEditor {
  constructor(host, callbacks) {
    this.host = host;
    this.callbacks = callbacks;
    this.pendingPort = null;
    this.activePointer = null;
    this.abort = new AbortController();
    this.build();
  }

  build() {
    const zoomOut = element('button', { type: 'button', 'aria-label': 'Zoom out', text: '−', onclick: () => this.zoom(0.8) });
    const zoomIn = element('button', { type: 'button', 'aria-label': 'Zoom in', text: '+', onclick: () => this.zoom(1.25) });
    this.zoomLabel = element('span', { class: 'zoom-label', text: '100%' });
    this.connectionHint = element('span', { class: 'graph-hint', text: 'Connect an output port to an input port. Drag the background to pan.' });
    const toolbar = element('div', { class: 'graph-toolbar' },
      element('button', { type: 'button', class: 'primary subtle', text: '+ Add node', 'data-testid': 'add-node', onclick: () => this.callbacks.addNode() }),
      element('button', { type: 'button', text: 'Duplicate', 'data-testid': 'duplicate-node', onclick: () => this.callbacks.duplicateSelection() }),
      element('button', { type: 'button', text: 'Delete', 'data-testid': 'delete-selection', onclick: () => this.callbacks.deleteSelection() }),
      this.externalToggle = element('button', { type: 'button', text: 'Enable external I/O blocks', 'data-testid': 'enable-external-io', onclick: () => this.callbacks.enableExternalIO() }),
      element('div', { class: 'toolbar-spacer' }),
      zoomOut, this.zoomLabel, zoomIn,
      element('button', { type: 'button', text: 'Fit', 'data-testid': 'fit-graph', onclick: () => this.fit() }));
    this.svg = svgElement('svg', { class: 'graph-svg', role: 'group', 'aria-label': 'Circuit graph. Select nodes and ports to edit their specifications.', tabindex: '0', 'data-testid': 'graph-canvas' });
    this.viewport = svgElement('g');
    const marker = svgElement('marker', { id: 'edge-arrow', viewBox: '0 0 10 10', refX: '9', refY: '5', markerWidth: '6', markerHeight: '6', orient: 'auto-start-reverse' }, svgElement('path', { d: 'M 0 0 L 10 5 L 0 10 z', fill: 'context-stroke' }));
    this.svg.append(svgElement('defs', {}, marker), this.viewport);
    this.svg.addEventListener('pointerdown', event => {
      if (event.target === this.svg && event.button === 0) {
        this.pendingPort = null;
        this.callbacks.select(null, event.shiftKey);
        this.startPan(event);
      }
    });
    this.svg.addEventListener('wheel', event => {
      event.preventDefault();
      this.zoom(event.deltaY > 0 ? 0.9 : 1.1, event);
    }, { passive: false });
    this.svg.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        this.pendingPort = null;
        this.connectionHint.textContent = 'Connection cancelled. Select an output port to begin again.';
      }
    });
    const signal = this.abort.signal;
    window.addEventListener('pointermove', event => this.movePointer(event), { signal });
    window.addEventListener('pointerup', () => this.endPointer(), { signal });
    window.addEventListener('pointercancel', () => this.endPointer(), { signal });
    this.host.replaceChildren(toolbar, this.svg, element('div', { class: 'graph-footer' }, this.connectionHint, element('span', { class: 'graph-key', text: 'Shift + click · multi-select' })));
  }

  destroy() { this.abort.abort(); }

  update(design, selected) {
    this.design = design;
    this.selected = selected;
    let view = design.layout.viewport;
    // Default symbols must be visible without making a layout edit on load.
    // The first explicit pan/zoom starts from this rendered view.
    if (hasExternalIO(design) && view.x === 0 && view.y === 0 && view.zoom === 1 && this.svg.getBoundingClientRect) {
      const rect = this.svg.getBoundingClientRect();
      const boxes = [...design.nodes.map(node => ({ ...position(design, node.id), width: NODE_WIDTH, height: nodeHeight(node) })), ...externalBlocks(design)];
      const minX = Math.min(...boxes.map(box => box.x)), minY = Math.min(...boxes.map(box => box.y));
      const maxX = Math.max(...boxes.map(box => box.x + box.width)), maxY = Math.max(...boxes.map(box => box.y + box.height));
      if (rect.width > 0 && rect.height > 0) {
        const zoom = Math.max(0.25, Math.min(1.25, (rect.width - 70) / (maxX - minX), (rect.height - 70) / (maxY - minY)));
        view = { x: (rect.width - (maxX - minX) * zoom) / 2 - minX * zoom, y: (rect.height - (maxY - minY) * zoom) / 2 - minY * zoom, zoom };
      }
    }
    this.renderedView = view;
    this.viewport.setAttribute('transform', `translate(${view.x} ${view.y}) scale(${view.zoom})`);
    this.zoomLabel.textContent = `${Math.round(view.zoom * 100)}%`;
    if (this.externalToggle) this.externalToggle.hidden = hasExternalIO(design);
    this.viewport.replaceChildren();
    for (const edge of design.edges) this.drawEdge(edge);
    for (const binding of design.external_io?.connections || []) this.drawExternalBinding(binding);
    for (const node of design.nodes) this.drawNode(node);
    for (const block of externalBlocks(design)) this.drawExternalBlock(block);
  }

  drawExternalBinding(binding) {
    const external = this.design.external_io.ports.find(port => port.id === binding.external_port_id);
    const block = externalBlocks(this.design).find(item => item.direction === external?.direction);
    const node = this.design.nodes.find(item => item.id === binding.node_id);
    if (!block || !node || !node.ports.some(port => port.id === binding.port_id)) return;
    const row = block.ports.findIndex(port => port.id === external.id);
    const outer = { x: block.x + (external.direction === 'input' ? block.width : 0), y: block.y + 81 + row * PORT_ROW };
    const at = position(this.design, node.id), offset = portOffset(node, binding.port_id, binding.instance_index);
    const inner = { x: at.x + offset.x, y: at.y + offset.y };
    const [source, target] = external.direction === 'input' ? [outer, inner] : [inner, outer];
    const bend = Math.max(45, Math.abs(target.x - source.x) * 0.48);
    const d = `M ${source.x} ${source.y} C ${source.x + bend} ${source.y}, ${target.x - bend} ${target.y}, ${target.x} ${target.y}`;
    const group = svgElement('g', { class: `graph-edge external-edge${this.selected?.kind === 'external_binding' && this.selected.id === binding.id ? ' selected' : ''}`, tabindex: '0', role: 'button', 'aria-label': externalBindingLabel(this.design, binding), 'data-external-binding-id': binding.id },
      svgElement('title', { text: externalBindingLabel(this.design, binding) }), svgElement('path', { d, class: 'edge-hit' }), svgElement('path', { d, class: 'edge-line', 'marker-end': 'url(#edge-arrow)' }));
    const select = event => { event.stopPropagation(); this.callbacks.select({ kind: 'external_binding', id: binding.id }); };
    group.addEventListener('click', select);
    group.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(event); } });
    this.viewport.append(group);
  }

  drawExternalBlock(block) {
    const selected = this.selected?.kind === 'external' && this.selected.direction === block.direction;
    const group = svgElement('g', { transform: `translate(${block.x} ${block.y})`, class: `graph-external${selected ? ' selected' : ''}`, tabindex: '0', role: 'button', 'aria-label': block.name, 'data-testid': `external-block-${block.direction}` });
    group.append(svgElement('rect', { width: block.width, height: block.height, rx: 12, class: 'external-body' }),
      svgElement('text', { x: 14, y: 29, class: 'node-title', text: block.name }),
      svgElement('text', { x: 14, y: 49, class: 'node-module', text: 'Top terminals · no RTL instance' }));
    if (!block.ports.length) group.append(svgElement('text', { x: 14, y: 81, class: 'port-name', text: 'Select to add terminals' }));
    for (const [row, port] of block.ports.entries()) {
      const output = block.direction === 'input';
      const x = output ? block.width : 0, y = 81 + row * PORT_ROW;
      const pending = this.pendingPort?.external_port_id === port.id;
      const portGroup = svgElement('g', { class: `graph-port ${output ? 'output' : 'input'}${pending ? ' pending' : ''}`, tabindex: '0', role: 'button', 'aria-label': `External ${port.direction} port ${port.name}, ${port.width} bits`, 'data-external-port-id': port.id },
        svgElement('title', { text: `${port.name} · ${port.protocol} · ${port.width} bits · ${port.signed ? 'signed' : 'unsigned'}` }),
        svgElement('circle', { cx: x, cy: y, r: 10, class: 'port-hit' }), svgElement('circle', { cx: x, cy: y, r: 5, class: 'port-dot' }),
        svgElement('text', { x: output ? block.width - 12 : 12, y: y + 4, 'text-anchor': output ? 'end' : 'start', class: 'port-name', text: `${truncate(port.name, 19)} [${port.width}]` }));
      const connect = event => {
        event.stopPropagation();
        if (output) {
          this.pendingPort = { external_port_id: port.id };
          this.callbacks.select({ kind: 'external', direction: block.direction, portId: port.id });
          this.connectionHint.textContent = `Connecting external ${port.name}. Select a matching node input; Esc cancels.`;
          this.update(this.design, this.selected);
        } else if (this.pendingPort && !this.pendingPort.external_port_id) {
          const source = this.pendingPort; this.pendingPort = null;
          this.callbacks.addExternalBinding(port.id, source);
        } else this.callbacks.select({ kind: 'external', direction: block.direction, portId: port.id });
      };
      portGroup.addEventListener('pointerdown', event => event.stopPropagation());
      portGroup.addEventListener('click', connect);
      portGroup.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); connect(event); } });
      group.append(portGroup);
    }
    const select = event => { event.stopPropagation(); this.callbacks.select({ kind: 'external', direction: block.direction }); };
    group.addEventListener('click', select);
    group.addEventListener('keydown', event => { if ((event.key === 'Enter' || event.key === ' ') && event.target === group) { event.preventDefault(); select(event); } });
    this.viewport.append(group);
  }

  drawEdge(edge) {
    const sourceNode = this.design.nodes.find(node => node.id === edge.source.node_id);
    const targetNode = this.design.nodes.find(node => node.id === edge.target.node_id);
    if (!sourceNode || !targetNode) return;
    const sourcePosition = position(this.design, sourceNode.id);
    const targetPosition = position(this.design, targetNode.id);
    const sourceOffset = portOffset(sourceNode, edge.source.port_id, edge.source.instance_index);
    const targetOffset = portOffset(targetNode, edge.target.port_id, edge.target.instance_index);
    const x1 = sourcePosition.x + sourceOffset.x, y1 = sourcePosition.y + sourceOffset.y;
    const x2 = targetPosition.x + targetOffset.x, y2 = targetPosition.y + targetOffset.y;
    const bend = Math.max(65, Math.abs(x2 - x1) * 0.48);
    const d = `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`;
    const selected = this.selected?.kind === 'edge' && this.selected.id === edge.id;
    const sourceName = sourceNode.name + instanceSuffix(edge.source.instance_index), targetName = targetNode.name + instanceSuffix(edge.target.instance_index);
    const group = svgElement('g', { class: `graph-edge${selected ? ' selected' : ''}`, tabindex: '0', role: 'button', 'aria-label': `Connection from ${sourceName} to ${targetName}`, 'data-edge-id': edge.id },
      svgElement('title', { text: `${sourceName} → ${targetName}\n${edge.behavior || 'No transfer specification yet'}` }),
      svgElement('path', { d, class: 'edge-hit' }),
      svgElement('path', { d, class: 'edge-line', 'marker-end': 'url(#edge-arrow)' }));
    const select = event => { event.stopPropagation(); this.callbacks.select({ kind: 'edge', id: edge.id }); };
    group.addEventListener('click', select);
    group.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(event); } });
    this.viewport.append(group);
  }

  drawNode(node) {
    const at = position(this.design, node.id);
    const selectedIds = this.selected?.kind === 'node' ? (this.selected.ids || [this.selected.id]) : [];
    const selected = selectedIds.includes(node.id);
    const shapeInfo = arrayShape(node);
    const group = svgElement('g', { transform: `translate(${at.x} ${at.y})`, class: `graph-node${selected ? ' selected' : ''}${shapeInfo ? ' array-node' : ''}`, tabindex: '0', role: 'button', 'aria-label': `Node ${node.name}, module ${node.module_name}${shapeInfo ? `, ${shapeInfo.rows} by ${shapeInfo.columns} instance array` : ''}`, 'data-node-id': node.id, 'data-testid': `node-${node.id}` });
    const shape = svgElement('rect', { width: NODE_WIDTH, height: nodeHeight(node), rx: '12', class: 'node-body' });
    group.append(svgElement('title', { text: `${node.name}\n${node.behavior || 'No behavior specification yet'}` }), shape,
      svgElement('rect', { x: '0', y: '0', width: NODE_WIDTH, height: '5', rx: '3', class: 'node-accent' }),
      svgElement('text', { x: '17', y: '31', class: 'node-title', text: truncate(node.name, 24) }),
      svgElement('text', { x: '17', y: '52', class: 'node-module', text: truncate(node.module_name, 29) }),
      svgElement('line', { x1: '0', y1: headerHeight(node), x2: NODE_WIDTH, y2: headerHeight(node), class: 'node-divider' }));
    if (shapeInfo) group.append(svgElement('text', { x: '17', y: '73', class: 'node-array-label', text: `${shapeInfo.rows} × ${shapeInfo.columns} array · shared definition` }));
    for (const port of displayPorts(node)) {
      const suffix = instanceSuffix(port.instance_index);
      const offset = portOffset(node, port.id, port.instance_index);
      const output = port.direction === 'output';
      const pending = this.pendingPort?.node_id === node.id && this.pendingPort?.port_id === port.id && instanceSuffix(this.pendingPort.instance_index) === suffix;
      const portGroup = svgElement('g', { class: `graph-port ${output ? 'output' : 'input'}${pending ? ' pending' : ''}`, tabindex: '0', role: 'button', 'aria-label': `${node.name}${suffix} ${port.direction} port ${port.name}, ${port.width} bits`, 'data-port-id': port.id, ...(suffix ? { 'data-instance-index': suffix } : {}) });
      portGroup.append(svgElement('title', { text: `${node.name}${suffix}.${port.name} · ${port.direction} · ${port.width} bits · ${port.signed ? 'signed' : 'unsigned'}\nSelect output then input to connect. Double-click to inspect.` }),
        svgElement('circle', { cx: offset.x, cy: offset.y, r: '10', class: 'port-hit' }),
        svgElement('circle', { cx: offset.x, cy: offset.y, r: '5', class: 'port-dot' }),
        svgElement('text', { x: output ? NODE_WIDTH - 12 : 12, y: offset.y + 4, 'text-anchor': output ? 'end' : 'start', class: 'port-name', text: `${truncate(port.name, suffix ? 9 : 15)}${suffix} [${port.width}]` }));
      portGroup.addEventListener('pointerdown', event => event.stopPropagation());
      const connect = event => {
        event.stopPropagation();
        if (output) {
          this.pendingPort = { node_id: node.id, port_id: port.id, ...(suffix ? { instance_index: port.instance_index } : {}) };
          this.callbacks.select({ kind: 'node', id: node.id, portId: port.id });
          this.connectionHint.textContent = `Connecting ${node.name}${suffix}.${port.name}. Select an input port; Esc cancels.`;
          this.update(this.design, this.selected);
        } else if (this.pendingPort) {
          const source = this.pendingPort;
          this.pendingPort = null;
          const target = { node_id: node.id, port_id: port.id, ...(suffix ? { instance_index: port.instance_index } : {}) };
          if (source.external_port_id) this.callbacks.addExternalBinding(source.external_port_id, target);
          else this.callbacks.addEdge(source, target);
          this.connectionHint.textContent = 'Connection created. Define its transfer behavior in the inspector.';
        } else this.callbacks.select({ kind: 'node', id: node.id, portId: port.id });
      };
      portGroup.addEventListener('click', connect);
      portGroup.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); connect(event); } });
      group.append(portGroup);
    }
    group.addEventListener('pointerdown', event => {
      if (event.button !== 0) return;
      event.stopPropagation();
      this.callbacks.select({ kind: 'node', id: node.id }, event.shiftKey);
      this.startNodeDrag(event, node.id);
    });
    group.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); event.stopPropagation(); this.callbacks.select({ kind: 'node', id: node.id }, event.shiftKey); }
    });
    this.viewport.append(group);
  }

  startNodeDrag(event, nodeId) {
    const ids = this.selected?.kind === 'node' && this.selected.ids?.includes(nodeId) ? this.selected.ids : [nodeId];
    this.activePointer = { kind: 'node', startX: event.clientX, startY: event.clientY, initial: structuredClone(this.design.layout), ids, moved: false };
    this.activePointer.original = structuredClone(this.design.layout);
    this.activePointer.initial.viewport = structuredClone(this.renderedView || this.design.layout.viewport);
  }

  startPan(event) {
    this.activePointer = { kind: 'pan', startX: event.clientX, startY: event.clientY, initial: structuredClone(this.design.layout), moved: false };
    this.activePointer.original = structuredClone(this.design.layout);
    this.activePointer.initial.viewport = structuredClone(this.renderedView || this.design.layout.viewport);
    this.svg.classList.add('panning');
  }

  movePointer(event) {
    const active = this.activePointer;
    if (!active) return;
    const dx = event.clientX - active.startX, dy = event.clientY - active.startY;
    if (!active.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
    active.moved = true;
    const layout = structuredClone(active.initial);
    if (active.kind === 'pan') { layout.viewport.x += dx; layout.viewport.y += dy; }
    else for (const id of active.ids) {
      const initial = Object.hasOwn(active.initial.nodes, id) ? active.initial.nodes[id] : { x: 80, y: 80 };
      Object.defineProperty(layout.nodes, id, { value: { x: Math.round(initial.x + dx / layout.viewport.zoom), y: Math.round(initial.y + dy / layout.viewport.zoom) }, enumerable: true, configurable: true, writable: true });
    }
    this.callbacks.previewLayout(layout);
  }

  endPointer() {
    const active = this.activePointer;
    this.activePointer = null;
    this.svg.classList.remove('panning');
    if (active?.moved) this.callbacks.commitLayout(active.original || active.initial);
  }

  zoom(factor, event) {
    const original = structuredClone(this.design.layout);
    const current = this.renderedView || original.viewport;
    const nextZoom = Math.max(0.25, Math.min(2, current.zoom * factor));
    const rect = this.svg.getBoundingClientRect();
    const centerX = event ? event.clientX - rect.left : rect.width / 2;
    const centerY = event ? event.clientY - rect.top : rect.height / 2;
    const ratio = nextZoom / current.zoom;
    const layout = structuredClone(original);
    layout.viewport = { x: centerX - (centerX - current.x) * ratio, y: centerY - (centerY - current.y) * ratio, zoom: nextZoom };
    this.callbacks.setLayout(layout);
  }

  fit() {
    if (!this.design.nodes.length && !hasExternalIO(this.design)) return;
    const rect = this.svg.getBoundingClientRect();
    const boxes = [...this.design.nodes.map(node => ({ ...position(this.design, node.id), width: NODE_WIDTH, height: nodeHeight(node) })), ...externalBlocks(this.design)];
    const minX = Math.min(...boxes.map(box => box.x)), minY = Math.min(...boxes.map(box => box.y));
    const maxX = Math.max(...boxes.map(box => box.x + box.width)), maxY = Math.max(...boxes.map(box => box.y + box.height));
    const zoom = Math.max(0.25, Math.min(1.25, (rect.width - 90) / (maxX - minX), (rect.height - 90) / (maxY - minY)));
    const layout = structuredClone(this.design.layout);
    layout.viewport = { x: (rect.width - (maxX - minX) * zoom) / 2 - minX * zoom, y: (rect.height - (maxY - minY) * zoom) / 2 - minY * zoom, zoom };
    this.callbacks.setLayout(layout);
  }
}

function truncate(text, length) { const value = String(text); return value.length > length ? `${value.slice(0, length - 1)}…` : value; }
