/** Shared PE definitions and explicitly indexed connection endpoints. Pure draft helpers. */
export function arrayShape(node) {
  const shape = node?.instance_array;
  return shape && Number.isInteger(shape.rows) && Number.isInteger(shape.columns)
    && shape.rows >= 1 && shape.rows <= 16 && shape.columns >= 1 && shape.columns <= 16
    ? shape : null;
}

export function instanceIndices(node) {
  const shape = arrayShape(node);
  if (!shape) return [null];
  return Array.from({ length: shape.rows * shape.columns }, (_, index) =>
    [Math.floor(index / shape.columns), index % shape.columns]);
}

export const instanceSuffix = index => Array.isArray(index) ? `[${index.join(',')}]` : '';

export function endpointValue(nodeId, portId, instanceIndex) {
  return JSON.stringify(Array.isArray(instanceIndex) ? [nodeId, portId, instanceIndex] : [nodeId, portId]);
}

export function parseEndpoint(value) {
  // IDs are opaque strings. Delimiters in names and IDs remain lossless.
  const [node_id, port_id, instance_index] = JSON.parse(value);
  return { node_id, port_id, ...(Array.isArray(instance_index) ? { instance_index } : {}) };
}

export function endpointsFor(design, direction) {
  return design.nodes.flatMap(node => instanceIndices(node).flatMap(index =>
    node.ports.filter(port => port.direction === direction).map(port => [
      endpointValue(node.id, port.id, index), `${node.name}${instanceSuffix(index)}.${port.name} · ${port.width} bits`,
    ])));
}

export function targetValue(target) {
  return JSON.stringify(Array.isArray(target.instance_index) ? [target.node_id, target.instance_index] : [target.node_id]);
}

export function parseTarget(value) {
  const [node_id, instance_index] = JSON.parse(value);
  return { node_id, ...(Array.isArray(instance_index) ? { instance_index } : {}) };
}

export function placementTargets(design) {
  return design.nodes.flatMap(node => instanceIndices(node).map(index => {
    const target = { node_id: node.id, ...(index ? { instance_index: index } : {}) };
    return [targetValue(target), `${node.name}${instanceSuffix(index)}`];
  }));
}

/** Do not silently delete indexed connections when changing an array shape. */
export function arrayResizeProblem(design, nodeId, nextShape) {
  const referenced = [
    ...design.edges.flatMap(edge => [edge.source, edge.target]),
    ...(design.physical_design?.regions || []).flatMap(region => region.targets || []),
  ].filter(endpoint => endpoint.node_id === nodeId);
  if (nextShape && (!Number.isInteger(nextShape.rows) || !Number.isInteger(nextShape.columns)
    || nextShape.rows < 1 || nextShape.rows > 16 || nextShape.columns < 1 || nextShape.columns > 16))
    return 'Array rows and columns must be whole numbers from 1 to 16.';
  if (referenced.some(endpoint => {
    const index = endpoint.instance_index;
    return nextShape ? !Array.isArray(index) || index.length !== 2 || !index.every(value => Number.isInteger(value) && value >= 0) || index[0] >= nextShape.rows || index[1] >= nextShape.columns
      : Array.isArray(index);
  })) return 'Connected ports or physical regions reference the current instance shape. Edit or remove those references before changing this definition.';
  return '';
}
