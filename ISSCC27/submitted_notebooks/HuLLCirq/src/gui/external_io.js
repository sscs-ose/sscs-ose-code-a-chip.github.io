/** Explicit top boundaries. These are draft graph symbols, never DUT nodes. */
import { element as el, field, badge } from './dom.js';
import { endpointsFor, endpointValue, parseEndpoint, instanceSuffix } from './design_instances.js';

export const hasExternalIO = design => Object.hasOwn(design || {}, 'external_io');
export const blankExternalIO = () => ({ version: 1, ports: [], connections: [] });
export const externalPorts = (design, direction) => (design.external_io?.ports || []).filter(port => !direction || port.direction === direction);
export const externalEndpointValue = id => JSON.stringify({ external_port_id: id });
export function parseGraphEndpoint(value) {
  const parsed = JSON.parse(value);
  return !Array.isArray(parsed) && parsed?.external_port_id ? parsed : parseEndpoint(value);
}
export function externalEndpointChoices(design, canvasDirection) {
  const direction = canvasDirection === 'output' ? 'input' : 'output';
  return externalPorts(design, direction).map(port => [externalEndpointValue(port.id), `External ${direction}: ${port.name} · ${port.width} bits`]);
}
export function expandedExternalPorts(design) {
  return externalPorts(design).flatMap(port => [
    { name: port.name, direction: port.direction, width: port.width, signed: port.signed },
    ...(port.protocol === 'valid_ready' ? [
      { name: `${port.name}_valid`, direction: port.direction, width: 1, signed: false },
      { name: `${port.name}_ready`, direction: port.direction === 'input' ? 'output' : 'input', width: 1, signed: false },
    ] : []),
  ]);
}
export function externalBindingLabel(design, binding) {
  const external = externalPorts(design).find(port => port.id === binding.external_port_id);
  const node = design.nodes.find(item => item.id === binding.node_id);
  const port = node?.ports.find(item => item.id === binding.port_id);
  const outer = external ? `External ${external.direction}: ${external.name}` : `Missing external port (${binding.external_port_id})`;
  const inner = node && port ? `${node.name}${instanceSuffix(binding.instance_index)}.${port.name}` : `Missing node port (${binding.node_id}/${binding.port_id})`;
  return external?.direction === 'output' ? `${inner} → ${outer}` : `${outer} → ${inner}`;
}
export function externalConnectionProblem(design, externalId, endpoint) {
  const external = externalPorts(design).find(port => port.id === externalId);
  const node = design.nodes.find(item => item.id === endpoint.node_id);
  const port = node?.ports.find(item => item.id === endpoint.port_id);
  if (!external || !port) return 'Select an external terminal and an existing node port.';
  if (!endpointsFor(design, external.direction).some(([value]) => value === endpointValue(endpoint.node_id, endpoint.port_id, endpoint.instance_index))) return 'Select the exact existing node instance and port.';
  if (external.direction !== port.direction) return 'External inputs feed node inputs; node outputs feed external outputs.';
  if (external.width !== port.width || external.signed !== port.signed || external.protocol !== port.protocol) return 'External and node ports must have the same width, signedness and protocol.';
  if (port.clock !== design.settings.clock_name || port.reset !== design.settings.reset_name) return 'The connected node must use the global clock and reset.';
  const sameEndpoint = item => endpointValue(item.node_id, item.port_id, item.instance_index) === endpointValue(endpoint.node_id, endpoint.port_id, endpoint.instance_index);
  if ((design.external_io.connections || []).some(item => item.external_port_id === externalId || sameEndpoint(item))) return 'A terminal or node endpoint is already bound. Remove that binding explicitly before replacing it.';
  if (design.edges.some(edge => sameEndpoint(edge.source) || sameEndpoint(edge.target))) return 'This node port already has an internal connection. Remove it explicitly before exposing the port.';
  return '';
}
export function externalArrayResizeProblem(design, nodeId, nextShape) {
  const invalid = (design.external_io?.connections || []).filter(item => item.node_id === nodeId).some(item => {
    const index = item.instance_index;
    return nextShape ? !Array.isArray(index) || index.length !== 2 || !index.every(value => Number.isInteger(value) && value >= 0) || index[0] >= nextShape.rows || index[1] >= nextShape.columns : Array.isArray(index);
  });
  return invalid ? 'External terminals reference the current instance shape. Remove or change those bindings explicitly before resizing.' : '';
}

export function externalBlocks(design, nodeWidth = 228) {
  if (!hasExternalIO(design)) return [];
  const positions = design.nodes.map(node => design.layout.nodes[node.id] || { x: 80, y: 80 });
  const minX = positions.length ? Math.min(...positions.map(at => at.x)) : 300;
  const maxX = positions.length ? Math.max(...positions.map(at => at.x + nodeWidth)) : 528;
  const y = positions.length ? Math.min(...positions.map(at => at.y)) : 80;
  return ['input', 'output'].map(direction => ({
    direction, name: direction === 'input' ? 'External inputs' : 'External outputs',
    x: direction === 'input' ? minX - 270 : maxX + 55, y, width: 200,
    height: 88 + Math.max(1, externalPorts(design, direction).length) * 28,
    ports: externalPorts(design, direction),
  }));
}

export function renderExternalInspector(host, design, selection, actions) {
  const direction = selection.direction;
  const title = direction === 'input' ? 'External inputs' : 'External outputs';
  host.append(el('div', { class: 'card-heading' }, el('span', { class: 'eyebrow', text: 'TOP INTERFACE' }), el('h2', { text: title }),
    el('p', { text: 'Declare top terminals and bind each to one exact node port. Clock and reset come from Global Settings. Save design records this draft.' })));
  const ports = externalPorts(design, direction);
  if (!ports.length) host.append(el('p', { class: 'empty-small', text: 'No terminals declared in this block yet.' }));
  for (const port of ports) {
    const change = (key, value) => actions.changePort(port.id, key, value);
    const bindings = (design.external_io.connections || []).filter(item => item.external_port_id === port.id);
    const choices = [['', 'Select an exact node port…'], ...endpointsFor(design, port.direction)];
    let target = '';
    host.append(el('section', { class: 'port-fields external-port-fields', 'data-external-port-fields': port.id },
      el('div', { class: 'port-heading' }, badge(port.direction), el('code', { text: port.id }),
        el('button', { type: 'button', class: 'icon-button danger', text: '×', 'aria-label': `Delete external port ${port.name}`, onclick: () => actions.deletePort(port.id) })),
      el('div', { class: 'form-grid' },
        field('External port name', port.name, value => change('name', value), { id: `external-name-${port.id}`, spellcheck: false }),
        field('Width (bits)', port.width, value => change('width', Number(value)), { id: `external-width-${port.id}`, type: 'number', min: 1, max: 4096, step: 1 }),
        field('Signedness', String(port.signed), value => change('signed', value === 'true'), { id: `external-signed-${port.id}`, choices: [['false', 'Unsigned'], ['true', 'Signed']] }),
        field('Protocol', port.protocol, value => change('protocol', value), { id: `external-protocol-${port.id}`, choices: [['valid_ready', 'valid / ready stream'], ['raw', 'Raw public signal']] })),
      el('p', { class: 'scope-note', text: port.protocol === 'valid_ready' ? `Physical pins: ${port.name}, ${port.name}_valid, ${port.name}_ready. Ready runs in the reverse direction.` : `One physical top pin: ${port.name}.` }),
      ...bindings.map(binding => el('div', { class: 'external-binding-row' }, el('p', { text: externalBindingLabel(design, binding) }),
        el('button', { type: 'button', text: 'Remove external connection', onclick: () => actions.removeBinding(binding.id) }))),
      field('Bind to node port', target, value => { target = value; }, { id: `external-target-${port.id}`, choices, disabled: bindings.length > 0 }),
      el('button', { type: 'button', text: 'Connect external port', disabled: bindings.length > 0 || choices.length < 2, onclick: () => {
        const value = host.querySelector(`#${CSS.escape(`external-target-${port.id}`)}`)?.value || target;
        if (!value) return actions.message('Select an exact node port first.');
        actions.addBinding(port.id, parseEndpoint(value));
      } })));
  }
  if (direction === 'input') for (const binding of design.external_io.connections.filter(item => !design.external_io.ports.some(port => port.id === item.external_port_id))) {
    host.append(el('div', { class: 'external-binding-row' }, el('p', { class: 'gate-reason', text: externalBindingLabel(design, binding) }),
      el('button', { type: 'button', text: 'Remove invalid external connection', onclick: () => actions.removeBinding(binding.id) })));
  }
  host.append(el('button', { type: 'button', text: direction === 'input' ? '+ Add external input' : '+ Add external output', 'data-testid': `add-external-${direction}`, onclick: () => actions.addPort(direction) }));
}
