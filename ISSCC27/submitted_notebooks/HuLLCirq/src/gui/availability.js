/** Display-only reasons why an operation cannot start; never changes execution gates. */
const LABELS = Object.freeze({
  implementation: 'Not implemented', prerequisite: 'Prerequisites missing',
  configuration: 'Tool setup required', connection: 'Connection required',
  input: 'Input required', unknown: 'Reason unavailable',
});

const ACTIONS = Object.freeze({
  implementation: 'Inspect implementation support', prerequisite: 'Inspect prerequisites',
  configuration: 'Open tool settings', connection: 'Check connection', input: 'Inspect required input',
});

const KINDS = Object.freeze({
  implementation: 'implementation', implementation_required: 'implementation',
  not_implemented: 'implementation', checker_not_implemented: 'implementation',
  unsupported_checker: 'implementation', stage_unimplemented: 'implementation',
  prerequisite: 'prerequisite', prerequisite_required: 'prerequisite',
  prerequisites_missing: 'prerequisite', candidate_required: 'prerequisite',
  synthesis_required: 'prerequisite', source_required: 'prerequisite', active_operation: 'prerequisite',
  configuration: 'configuration', configuration_required: 'configuration', tool_setup_required: 'configuration',
  connection: 'connection', connection_required: 'connection',
  input: 'input', input_required: 'input', instruction_revision_required: 'input',
  unsaved: 'input', unsaved_changes: 'input', dirty: 'input', conflict: 'input', source_conflict: 'input',
  repair_guidance_required: 'input', repair_instruction_required: 'input',
});

const CODES = Object.freeze({
  verification_contract_missing: 'implementation', unsupported_verification_contract: 'implementation',
  verification_implementation_required: 'implementation',
  unsupported_verification_template: 'implementation', unsupported_checker: 'implementation',
  checker_not_implemented: 'implementation', stage_not_implemented: 'implementation',
  unsupported_integration: 'implementation',
  candidate_required: 'prerequisite', synthesis_required: 'prerequisite',
  accepted_candidate_required: 'prerequisite', accepted_synthesis_required: 'prerequisite',
  workflow_prerequisite: 'prerequisite', prerequisite_missing: 'prerequisite',
  compiler_unavailable: 'configuration', invalid_compiler: 'configuration', unsupported_compiler: 'configuration',
  simulator_unavailable: 'configuration', invalid_simulator: 'configuration', unsupported_simulator: 'configuration',
  synthesizer_unavailable: 'configuration', invalid_synthesizer: 'configuration', unsupported_synthesizer: 'configuration',
  tool_unavailable: 'configuration', invalid_tool: 'configuration', tool_configuration_missing: 'configuration',
  provider_unavailable: 'connection', connection_failed: 'connection', connection_refused: 'connection',
  network_error: 'connection', provider_not_connected: 'connection',
  context_budget: 'input', global_context_budget: 'input', context_window_exceeded: 'input',
  repeated_repair_guidance: 'input', repair_guidance_repeated: 'input', repair_reconsideration_required: 'input',
  repair_guidance_missing: 'input', missing_repair_guidance: 'input',
  concrete_repair_guidance_required: 'input', concrete_repair_instruction_required: 'input',
  repair_instruction_required: 'input', repair_analysis_required: 'input',
  invalid_verification_vectors: 'input', invalid_verification_contract: 'input',
  verification_input_required: 'input', unsupported_language: 'input', invalid_input: 'input',
});

const DEFAULTS = Object.freeze({
  implementation: 'The connected service does not implement this operation for the saved input.',
  prerequisite: 'A required earlier result is missing or is not current. Inspect the prerequisite evidence.',
  configuration: 'A required tool or its trusted configuration is unavailable.',
  connection: 'The required service connection is unavailable.',
  input: 'Required input must be completed or revised before this request can start.',
  unknown: 'No specific reason was recorded. Inspect the saved operation details.',
});

const normalized = value => typeof value === 'string' ? value.trim().toLowerCase().replace(/[\s-]+/g, '_') : '';
const text = value => typeof value === 'string' ? value.trim() : '';
const object = value => value && typeof value === 'object' && !Array.isArray(value) ? value : {};

/**
 * Prefer structured readiness/kind/code over conservative legacy-text matching.
 * A server's raw "Blocked" status is not a diagnosis. Original records are kept
 * by callers; this helper supplies a cause label for the current display only.
 */
export function availabilityReason(value = {}) {
  const source = typeof value === 'string' ? { message: value } : object(value);
  const readiness = object(source.readiness);
  const reason = object(source.reason);
  const diagnostics = Array.isArray(source.diagnostics) ? source.diagnostics.map(object) : [];
  const sourceDiagnostics = [source, readiness, reason].map(item => object(item.source_diagnostic));
  const records = [source, readiness, reason, ...diagnostics, ...sourceDiagnostics];
  const message = text(source.message) || text(source.reason) || text(reason.message) ||
    text(readiness.message) || diagnostics.map(item => text(item.message)).find(Boolean) || '';
  const specificMessage = sourceDiagnostics.map(item => text(item.message)).find(item => item &&
    !/no structured behavioral verification contract/i.test(item)) || '';
  const missingRepairGuidance = /no supported concrete repair method/i.test(message) || records.some(item =>
    ['repair_guidance_required', 'repair_guidance_missing', 'missing_repair_guidance',
      'concrete_repair_guidance_required', 'concrete_repair_instruction_required',
      'repair_instruction_required', 'repair_analysis_required'].includes(normalized(item.code || item.kind)));
  let kind = records.map(item => KINDS[normalized(item.kind)] || KINDS[normalized(item.status)]).find(Boolean);
  if (!kind) kind = records.map(item => CODES[normalized(item.code)]).find(Boolean);
  const legacyContract = /no structured behavioral verification contract/i.test(message) ||
    (!message && records.some(item => normalized(item.code) === 'verification_contract_missing'));
  if (!kind) {
    if (/not implemented|checker implementation|no supported (?:behavioral )?checker|unsupported (?:behavioral )?(?:checker|verification (?:template|contract))|no structured behavioral verification contract|currently integrates the six declared NPU node types/i.test(message)) kind = 'implementation';
    else if (/(?:compiler|simulator|synthesizer|tool).*(?:not configured|unavailable|not installed)|(?:configure|configuration).*(?:compiler|simulator|synthesizer)|trusted (?:fixed )?tool configuration.*required|save (?:an LLM provider profile|the edited provider settings) in Global Settings/i.test(message)) kind = 'configuration';
    else if (missingRepairGuidance || /(?:context window|input budget).*(?:exceed|reduce|increase)|exceeds?.*(?:context window|input budget)|same repair (?:plan|guidance).*unresolved|(?:revise|reconsider).*(?:repair|correction)|supply .*vectors/i.test(message)) kind = 'input';
    else if (/(?:current|accepted|same RTL).*(?:S04|S05|netlist|candidate).*(?:required|missing)|(?:S04|S05|netlist|candidate).*(?:must be accepted|needs a current)|needs a current accepted S0[45]|prerequisite.*(?:missing|required)|complete .*prerequisite|no current failed S05 result matches the latest RTL candidate|adopt (?:the latest )?current S\d+|waiting for current accepted|all six exact adopted node sources must remain current|accept a current node RTL candidate|accept node netlist verification results/i.test(message)) kind = 'prerequisite';
    else if (/save or reopen the current design first|save the current design before/i.test(message)) kind = 'input';
    else if (/connection (?:refused|failed|required)|not connected|service (?:offline|unreachable)|provider.*(?:unreachable|offline)/i.test(message)) kind = 'connection';
    else kind = 'unknown';
  }
  // Legacy backends use this code when they cannot recognize an executable
  // contract. It does not prove that the user's saved test requirements are absent.
  const displayMessage = kind === 'input' && missingRepairGuidance
    ? 'No concrete repair instruction is prepared for this diagnostic. Enter a correction in Additional instruction, or prepare an analysis and review its proposed changes. Then prepare a new repair preview.'
    : specificMessage || (kind === 'implementation' && legacyContract
    ? 'No supported executable behavioral checker could be built from the saved specification. This does not mean the saved test requirements are absent.'
    : message && normalized(message) !== 'blocked' ? message : DEFAULTS[kind]);
  return { kind, label: LABELS[kind], message: displayMessage,
    ...(kind === 'input' && missingRepairGuidance ? { actionLabel: 'Add or review repair instructions' }
      : ACTIONS[kind] ? { actionLabel: ACTIONS[kind] } : {}) };
}
