import { element as el, field, badge, downloadJson } from './dom.js';
import { sessionFetch, setWorkspaceSession, workspaceSession } from './workspace_transport.js';

const safe = value => String(value || 'HuLLCirq').replace(/[^a-z0-9_.-]/gi, '_');
const identifier = value => String(value || 'system_top').replace(/[^a-z0-9_]/gi, '_').replace(/^([0-9])/, '_$1');
const itemId = item => item?.id || item?.project_id || item?.system_id || item?.component_id;
const folderName = name => String(name || 'Untitled project').trim().replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_').replace(/[. ]+$/, '') || 'Untitled project';
const childDirectory = (parent, name) => `${parent.replace(/[\\/]+$/, '')}${parent.includes('\\') ? '\\' : '/'}${folderName(name)}`;

/** Project commands live outside the fourteen circuit-design stages. */
export class WorkspaceManager {
  constructor(callbacks) {
    this.callbacks = callbacks;
    this.data = { projects: [], library: [], recent: [], trash: [], active: null };
    this.busy = false;
    this.tab = 'projects';
    this.selectedProject = null;
    this.formDialog = null;
    this.dialog = document.getElementById('workspace-dialog');
    this.content = document.getElementById('workspace-dialog-content');
    this.dialog.addEventListener('cancel', event => { if (!this.data.active?.project_id) event.preventDefault(); });
    document.getElementById('workspace-home').addEventListener('click', () => this.show('projects'));
    document.getElementById('workspace-library').addEventListener('click', () => this.show('library'));
    document.getElementById('workspace-close-dialog').addEventListener('click', () => this.dialog.close());
  }

  async initialize() {
    let data;
    try { data = await this.callbacks.request('workspace'); }
    catch (error) {
      if (error.status !== 404) throw error;
      document.getElementById('workspace-switcher').hidden = true;
      document.getElementById('workspace-home').hidden = true;
      document.getElementById('workspace-library').hidden = true;
      return null;
    }
    this.receive(data.workspace || data, true);
    if (!this.data.active?.project_id) this.show('projects', false);
    return this.data;
  }

  receive(data, initialize = false) {
    if (!data) return;
    const library = data.library || data.components || [];
    const grouped = new Map();
    for (const entry of library) {
      if (Array.isArray(entry.versions)) { grouped.set(entry.id || entry.component_id, entry); continue; }
      const key = entry.id || entry.component_id;
      if (!grouped.has(key)) grouped.set(key, { ...entry, versions: [] });
      grouped.get(key).versions.push(entry);
    }
    this.data = { ...data, projects: data.projects || [], library: [...grouped.values()], recent: data.recent || [], trash: data.trash || [] };
    if (initialize) setWorkspaceSession(data.active?.session_id);
    if (!this.selectedProject || !this.projects().some(project => itemId(project) === this.selectedProject)) this.selectedProject = data.active?.project_id || itemId(this.projects()[0]);
    this.renderChrome();
    if (this.dialog.open) this.render();
  }

  projects() { return this.data.projects; }
  project(id = this.data.active?.project_id) { return this.projects().find(item => itemId(item) === id); }
  systems(project = this.project()) { return project?.systems || []; }
  system() { return this.systems().find(item => itemId(item) === this.data.active?.system_id); }
  contextCurrent() { return (this.data.active?.session_id || null) === workspaceSession(); }
  arrayVariantAvailable() {
    const design = this.callbacks.project()?.design;
    return this.contextCurrent() && !!this.data.active?.project_id && design?.nodes?.length === 11
      && ['npu2-pe00', 'npu2-pe01', 'npu2-pe10', 'npu2-pe11'].every(id => design.nodes.some(node => node.id === id && !node.instance_array));
  }

  async show(tab = 'projects', refresh = true) {
    this.callbacks.flush?.();
    this.tab = tab;
    if (refresh) {
      try { const data = await this.callbacks.request('workspace'); this.receive(data.workspace || data); }
      catch (error) { this.callbacks.notify(error.message, 'error'); }
    }
    this.render();
    if (!this.dialog.open) this.dialog.showModal();
  }

  button(text, action, options = {}) {
    return el('button', { type: 'button', text, disabled: this.busy, onclick: async () => {
      try { await action(); }
      catch (error) { this.commandError = error.message; this.callbacks.notify(error.message, 'error'); this.render(); }
    }, ...options });
  }

  async operate(action, body = {}, { context = false, protect = false, message = 'Workspace updated.', progress = 'Working with the local service…' } = {}) {
    if (this.busy) return;
    try {
      if ((context || protect) && !(await this.callbacks.beforeLeave())) return;
      this.commandError = null; this.commandProgress = progress;
      this.busy = true; this.render(); this.renderChrome();
      const result = await this.callbacks.request(`workspace/${action}`, body);
      this.receive(result.workspace || result);
      if (context || Object.hasOwn(result, 'project') && this.callbacks.identityChanged?.(result.workspace?.active)) {
        // Reload intentionally tears down all pending pollers, editors and undo
        // stacks together. The prior browser draft remains in its scoped key.
        this.callbacks.activate(result);
        return;
      }
      if (result.project) this.callbacks.updated?.(result.project, action);
      this.callbacks.toast(message);
    } catch (error) { this.commandError = error.message; this.callbacks.notify(error.message, 'error'); }
    finally { this.busy = false; this.commandProgress = null; this.render(); this.renderChrome(); }
  }

  open(project, system) {
    return this.operate('open', { project_id: itemId(project), system_id: itemId(system || this.systems(project)[0]), defer_project_view: true },
      { context: true, progress: `Opening ${project.name || itemId(project)}… Saved results load when you select their stage.` });
  }

  renderChrome() {
    const host = document.getElementById('workspace-switcher');
    if (!host) return;
    const active = this.data.active?.project_id ? this.data.active : null;
    const project = this.project();
    const projectSelect = el('select', { 'aria-label': 'Active project', 'data-testid': 'workspace-project-select', disabled: this.busy || !active, onchange: event => {
      const target = this.project(event.target.value); if (target) this.open(target);
      event.target.value = active?.project_id || '';
    } }, !active ? el('option', { value: '', text: 'No project open' }) : null,
    this.projects().map(item => el('option', { value: itemId(item), text: item.name || itemId(item) })));
    projectSelect.value = active?.project_id || '';
    const systemSelect = el('select', { 'aria-label': 'Active system', 'data-testid': 'workspace-system-select', disabled: this.busy || !active, onchange: event => {
      const target = this.systems(project).find(item => itemId(item) === event.target.value); if (target) this.open(project, target);
      event.target.value = active?.system_id || '';
    } }, !active ? el('option', { value: '', text: 'No system' }) : null,
    this.systems(project).map(item => el('option', { value: itemId(item), text: item.name || itemId(item) })));
    systemSelect.value = active?.system_id || '';
    host.replaceChildren(...[el('label', {}, el('span', { text: 'PROJECT' }), projectSelect), el('label', {}, el('span', { text: 'SYSTEM' }), systemSelect),
      active?.read_only ? badge('Read-only snapshot', 'neutral') : active ? badge('Editable design', 'teal') : null,
      active ? this.button('+ System', () => this.newSystem(project), { 'data-testid': 'workspace-add-system' }) : null].filter(Boolean));
  }

  render() {
    const close = document.getElementById('workspace-close-dialog');
    close.hidden = !this.data.active?.project_id;
    const tabs = el('nav', { class: 'workspace-home-tabs', 'aria-label': 'Workspace sections' },
      ...[['projects', 'Projects'], ['library', 'Component Library'], ['trash', `Trash (${this.data.trash.length})`]].map(([id, text]) => this.button(text, () => { this.tab = id; this.render(); }, { class: id === this.tab ? 'primary subtle' : '', 'aria-current': id === this.tab ? 'page' : null, 'data-testid': `workspace-tab-${id}` })));
    const body = el('div', { class: 'workspace-home-body' });
    this.content.replaceChildren(tabs, body);
    if (this.busy) body.append(el('p', { role: 'status', text: this.commandProgress || 'Working with the local service…', 'data-testid': 'workspace-command-status' }));
    if (this.commandError) body.append(el('div', { class: 'workspace-notice' },
      el('p', { role: 'alert', text: this.commandError }),
      this.button('Refresh Projects', () => this.show('projects', true), {
        'data-testid': 'workspace-refresh-projects', title: 'Read saved project status without repeating the previous operation.' })));
    if (!this.contextCurrent()) body.append(el('div', { class: 'workspace-notice' }, el('strong', { text: 'The active workspace changed in another window.' }),
      el('p', { text: 'This page keeps its own draft. Reconnect explicitly before using the active workspace.' }), this.button('Preserve draft and reconnect', async () => {
        if (!(await this.callbacks.beforeLeave())) return;
        setWorkspaceSession(this.data.active?.session_id); this.callbacks.activate({ workspace: this.data });
      }, { 'data-testid': 'workspace-reconnect' })));
    if (this.tab === 'library') this.renderLibrary(body); else if (this.tab === 'trash') this.renderTrash(body); else this.renderProjects(body);
  }

  renderProjects(host) {
    host.append(el('div', { class: 'workspace-home-intro' }, el('div', {}, el('h2', { text: 'Your design projects' }),
      el('p', { text: 'A project contains independent systems, shared component packages and preserved design history. Choose one system for the design stages.' })),
      el('div', { class: 'workspace-actions' }, this.button('New project', () => this.newProject(), { class: 'primary', 'data-testid': 'workspace-new-project' }),
        this.button('Open project folder', () => this.openDirectory(), { 'data-testid': 'workspace-open-directory' }),
        this.button('Restore backup', () => this.upload('restore'), { 'data-testid': 'workspace-restore' }),
        this.button('Restore evidence package', () => this.upload('evidence'), { 'data-testid': 'workspace-restore-evidence' }),
        this.button('Paste evidence JSON', () => this.pasteEvidence(), { 'data-testid': 'workspace-paste-evidence' }))));
    const recent = this.data.recent.map(entry => {
      const project = this.project(entry.project_id || itemId(entry));
      const system = this.systems(project).find(item => itemId(item) === entry.system_id) || this.systems(project)[0];
      return project && system ? this.button(`${project.name} / ${system.name}`, () => this.open(project, system), { class: 'recent-project' }) : null;
    }).filter(Boolean).slice(0, 6);
    if (recent.length) host.append(el('section', { class: 'workspace-recent' }, el('span', { class: 'eyebrow', text: 'RECENTLY OPENED' }), el('div', { class: 'workspace-actions' }, recent)));
    if (this.arrayVariantAvailable()) host.append(el('section', { class: 'workspace-notice' },
      el('h3', { text: 'Shared PE array variant' }),
      el('p', { text: 'Create a separate project with one shared 2 × 2 PE definition: 8 definitions, 11 physical instances. The original saved workload and expected values are retained; its adopted results stay only in the original project. New verification and layout are required.' }),
      this.button('Create PE array variant', () => this.newArrayVariant(), { 'data-testid': 'workspace-create-array-variant' })));
    const grid = el('div', { class: 'workspace-project-grid' });
    for (const project of this.projects()) {
      const systems = this.systems(project);
      const current = this.data.active?.project_id === itemId(project);
      const card = el('section', { class: `card workspace-project-card${current ? ' active' : ''}` },
        el('div', { class: 'workspace-card-title' }, el('div', {}, el('h3', { text: project.name || itemId(project) }), el('code', { text: itemId(project) })), current ? badge('Open', 'teal') : null),
        project.directory ? el('p', { class: 'workspace-project-directory', text: project.directory }) : null,
        el('div', { class: 'workspace-actions' }, this.button('Open', () => this.open(project), { class: 'primary subtle', 'data-testid': `workspace-open-${itemId(project)}` }),
          this.button('Rename', () => this.rename('project', project)), this.button('Duplicate', () => this.duplicate('project', project)),
          this.button('Download backup', () => this.download(`workspace/backup/${encodeURIComponent(itemId(project))}`, `${safe(project.name)}.hullcirq-backup.json`)),
          this.button('Download evidence package', () => this.exportEvidence(project), { 'data-testid': `workspace-export-evidence-${itemId(project)}` }),
          this.button('Inspect evidence package', () => this.inspectEvidence(project), { 'data-testid': `workspace-inspect-evidence-${itemId(project)}` }),
          this.button('Delete project', () => this.deleteProject(project), { 'data-testid': `workspace-delete-${itemId(project)}` }),
          current ? this.button('Close project', () => this.operate('close', {}, { context: true }), { 'data-testid': 'workspace-close-project' }) : null),
        el('div', { class: 'workspace-systems' }, systems.map(system => el('div', { class: 'workspace-system-row' }, el('div', {}, el('strong', { text: system.name || itemId(system) }), el('small', { text: `Top: ${system.top_module || system.module_name || 'Not specified'}` })),
          system.read_only ? badge('Read-only', 'neutral') : null,
          el('div', { class: 'workspace-actions' }, this.button('Open system', () => this.open(project, system)),
            this.button('Rename', () => this.rename('system', system, project)), this.button('Duplicate', () => this.duplicate('system', system, project))))),
          this.button('+ Add system', () => this.newSystem(project), { 'data-testid': `workspace-new-system-${itemId(project)}` })));
      grid.append(card);
    }
    host.append(grid);
    if (!this.projects().length) host.append(el('p', { class: 'workspace-empty', text: 'Create a project to begin. New systems start with an empty graph and no adopted results.' }));
    this.renderLegacyBackups(host);
  }

  async deleteProject(project) {
    const projectId = itemId(project), revision = project.management_revision;
    const count = this.systems(project).length;
    const confirmed = await this.form('Delete project', [],
      `“${project.name}” contains ${count} ${count === 1 ? 'system' : 'systems'}. Move this project to Trash? Its folder, RTL, results and history stay in place. You can restore it from Trash. Shared component packages remain available.`, 'Move to Trash');
    if (!confirmed) return;
    this.tab = 'trash';
    await this.operate('delete-project', { project_id: projectId, expected_project_revision: revision },
      { context: this.data.active?.project_id === projectId, protect: true, message: 'Project moved to Trash. Its files are retained.', progress: `Moving ${project.name} to Trash…` });
  }

  renderTrash(host) {
    host.append(el('div', { class: 'workspace-home-intro' }, el('div', {}, el('h2', { text: 'Project Trash' }),
      el('p', { text: 'Deleted projects are hidden from Projects. Their folders and complete history are retained in place. Restore returns the same project and system identities; it does not run tools.' }))));
    const grid = el('div', { class: 'workspace-project-grid' });
    for (const entry of this.data.trash) {
      const project = entry.project;
      grid.append(el('section', { class: 'card workspace-project-card', 'data-testid': `workspace-trash-${entry.id}` },
        el('h3', { text: project.name }), el('code', { text: itemId(project) }),
        el('p', { text: `${this.systems(project).length} system(s) · Deleted ${entry.deleted_at}` }),
        el('p', { class: 'workspace-project-directory', text: project.directory }),
        this.button('Restore project', async () => {
          await this.operate('restore-project', { trash_id: entry.id, expected_project_revision: project.management_revision },
            { message: 'Project restored. Open it from Projects to continue.', progress: `Restoring ${project.name}…` });
        }, { class: 'primary subtle', 'data-testid': `workspace-restore-${entry.id}` })));
    }
    host.append(grid);
    if (!this.data.trash.length) host.append(el('p', { class: 'workspace-empty', text: 'Trash is empty.' }));
  }

  async newProject() {
    const values = await this.form('New project', [['name', 'Project name', 'Untitled project'], ['project_directory', 'Project folder', '', { required: false, maxlength: 4096, hint: 'Enter the full new or empty folder path, or choose its parent. Leave blank to use the managed workspace location.', folder: 'parent' }], ['system_name', 'First system name', 'Main system'], ['top_module', 'Top module', 'system_top']]);
    if (values) {
      if (!values.project_directory) delete values.project_directory;
      await this.operate('create-project', values, { context: true });
    }
  }

  async newArrayVariant() {
    if (!this.arrayVariantAvailable()) return;
    const values = await this.form('Create PE array variant', [['name', 'New project name', `${this.project()?.name || 'NPU'} PE array`]],
      'This explicit action creates and opens a separate project from the saved 11-node design. It does not modify the original project, generate RTL, start tools, or copy acceptance.', 'Create separate project');
    if (values) await this.operate('array-variant', { project_id: this.data.active.project_id, system_id: this.data.active.system_id, ...values },
      { context: true, protect: true, progress: 'Creating the separate shared PE array project…', message: 'Fresh PE array project created; original results preserved.' });
  }

  async openDirectory() {
    const values = await this.form('Open project folder', [['directory', 'Existing project folder', '', { maxlength: 4096, folder: 'existing', hint: 'Choose the folder containing the HuLLCirq project manifest.' }]]);
    if (values) await this.operate('open-directory', values, { context: true });
  }

  async newSystem(project) {
    if (!project) return;
    const values = await this.form('Add system', [['name', 'System name', 'New system'], ['top_module', 'Top module', 'system_top']]);
    if (values) await this.operate('create-system', { project_id: itemId(project), ...values }, { context: true });
  }

  async rename(kind, item, project = item) {
    const values = await this.form(`Rename ${kind}`, [['name', `${kind === 'project' ? 'Project' : 'System'} name`, item.name || '']]);
    if (values) await this.operate(`rename-${kind}`, { project_id: itemId(project), ...(kind === 'system' ? { system_id: itemId(item) } : {}), ...values }, { protect: true });
  }

  async duplicate(kind, item, project = item) {
    const values = await this.form(`Duplicate ${kind}`, [['name', 'Copy name', `${item.name || 'Design'} copy`]], 'The copy receives new identities and a fresh execution history. Prior adopted results are retained only in the source.');
    if (values) await this.operate(`duplicate-${kind}`, { project_id: itemId(project), ...(kind === 'system' ? { system_id: itemId(item) } : {}), ...values }, { context: true });
  }

  renderLibrary(host) {
    const project = this.callbacks.project();
    host.append(el('div', { class: 'workspace-home-intro' }, el('div', {}, el('h2', { text: 'Reusable component packages' }),
      el('p', { text: 'Publish a whole system or selected nodes. Each immutable version records its source, interfaces and dependencies. Instantiation creates editable graph nodes with pinned provenance; integration results must be verified separately.' })),
      el('div', { class: 'workspace-actions' }, this.button('Publish current system', () => this.publish(false), { disabled: this.busy || !project.design, 'data-testid': 'workspace-publish-system' }),
        this.button('Publish selected nodes', () => this.publish(true), { disabled: this.busy || !project.design || !this.callbacks.selection().length, 'data-testid': 'workspace-publish-selection' }),
        this.button('Import component package', () => this.upload('component'), { 'data-testid': 'workspace-import-component' }))));
    const grid = el('div', { class: 'workspace-project-grid' });
    for (const component of this.data.library) {
      const componentId = component.component_id || component.id;
      const versions = Array.isArray(component.versions) ? component.versions : [component];
      const select = el('select', { 'aria-label': `Version of ${component.name}` }, versions.map(entry => {
        const value = typeof entry === 'string' || typeof entry === 'number' ? entry : entry.version;
        return el('option', { value, text: `Version ${value}` });
      }));
      const versionInfo = el('div', { class: 'workspace-component-info' });
      const showVersion = () => {
        const entry = versions.find(value => String(value?.version ?? value) === select.value) || component;
        const ports = entry.public_ports || component.public_ports || [];
        versionInfo.replaceChildren(el('p', { text: entry.source?.system_name ? `Source: ${entry.source.system_name}` : `${entry.node_count ?? component.node_count ?? 'Graph'} node(s) · Interface package` }),
          ports.length ? el('ul', { class: 'workspace-port-list' }, ports.map(port => el('li', { text: `${port.name || port.port_id || 'Port'} · ${port.direction || ''} · ${port.width ?? '?'} bits · ${port.protocol || 'raw'}` }))) : el('small', { text: 'Public interfaces are included in the downloaded package.' }),
          el('code', { text: entry.sha256 || entry.package_sha256 || '' }));
      };
      select.addEventListener('change', showVersion); showVersion();
      grid.append(el('section', { class: 'card workspace-project-card' }, el('div', { class: 'workspace-card-title' }, el('div', {}, el('h3', { text: component.name || componentId }), el('code', { text: componentId })), badge('Pinned versions', 'neutral')), select, versionInfo,
        el('div', { class: 'workspace-actions' }, this.button('Download package', () => this.download(`workspace/component/${encodeURIComponent(componentId)}/${encodeURIComponent(select.value)}`, `${safe(component.name)}-v${safe(select.value)}.hullcirq-component.json`)),
          this.button('Instantiate in graph', () => this.instantiate(component, select.value), { class: 'primary subtle', disabled: this.busy || !project.design || this.data.active?.read_only, 'data-testid': `workspace-instantiate-${componentId}` }))));
    }
    host.append(grid);
    if (!this.data.library.length) host.append(el('p', { class: 'workspace-empty', text: 'No packages yet. Publish a saved system or import a component package.' }));
    const instances = project.design?.component_instances || project.design?.components || [];
    if (instances.length) host.append(el('section', { class: 'workspace-instance-list' }, el('h3', { text: 'Pinned instances in the current system' }), ...instances.map(instance => el('p', {}, el('strong', { text: instance.instance_name || instance.name || instance.id }), ' · ', el('code', { text: `${instance.component_id || '?'} @ ${instance.version || instance.component_version || '?'}` })) )));
  }

  async publish(selected) {
    const p = this.callbacks.project();
    if (!p.design) return;
    if (!(await this.callbacks.beforeLeave({ publishing: true }))) return;
    const nodeIds = selected ? this.callbacks.selection() : p.design.nodes.map(node => node.id);
    if (!nodeIds.length) { this.callbacks.notify('Add at least one node before publishing a component.', 'warning'); return; }
    const values = await this.form('Publish component version', [['name', 'Component name', selected ? 'Selected component' : this.system()?.name || p.design.project.name]], 'The package preserves graph intent and public port contracts. It does not grant acceptance to a future integration. Publishing the same component name creates its next immutable version.');
    if (values) {
      const existing = this.data.library.filter(item => item.name === values.name);
      if (existing.length > 1) { this.callbacks.notify('More than one component uses this name. Choose a unique component name for this publication.', 'warning'); return; }
      await this.operate('publish-component', { ...values, node_ids: nodeIds, ...(existing.length === 1 ? { component_id: existing[0].id || existing[0].component_id } : {}) }, { message: 'Component version published. Its source and interface are pinned.' });
    }
  }

  async instantiate(component, version) {
    let p = this.callbacks.project();
    if (!p.design) return;
    const values = await this.form('Instantiate component', [['instance_name', 'Instance name', identifier(component.name || 'component')]], 'Nodes and internal connections are copied into the current graph with new IDs. Connect their public ports in the Graph Editor. No validation or adoption is performed by this operation.');
    if (values) {
      if (!(await this.callbacks.beforeLeave())) return;
      p = this.callbacks.project();
      await this.operate('instantiate', { component_id: component.component_id || component.id, version, ...values, expected_revision_id: p.envelope.revision.id }, { message: 'Component instantiated. Review the graph interfaces and connections.' });
    }
  }

  upload(kind) {
    const input = el('input', { type: 'file', accept: '.json,application/json', 'aria-label': kind === 'evidence' ? 'Portable evidence package' : kind === 'restore' ? 'Project backup file' : 'Component package file' });
    input.addEventListener('change', async () => {
      const file = input.files[0]; if (!file) return;
      try {
        if (kind === 'evidence' && file.size > 120 * 1024 * 1024) throw new Error('Evidence packages must be at most 120 MiB. No project was changed.');
        const raw = await file.text();
        if (kind === 'restore' || kind === 'evidence') {
          let contents; try { contents = JSON.parse(raw); } catch { throw new Error('This file is not valid JSON. The current project has not changed.'); }
          const values = await this.form(kind === 'evidence' ? 'Restore portable evidence package' : 'Restore project backup', [['name', 'Restored project name', `${contents.project?.name || contents.name || 'Project'} restored`]],
            'Restore creates a separate read-only project. Original provenance is retained, not executed. Inspect evidence downloads and Functional Maps from Projects. Duplicate a system for editable work; imported acceptance does not qualify this host.');
          // Parse only the display name. Send the original JSON text so source
          // snapshots inside pinned packages retain integers beyond JS Number.
          if (values) await this.operate(kind === 'evidence' ? 'restore-evidence' : 'restore', { bundle_text: raw, ...values }, { context: true, progress: 'Checking and restoring the raw evidence package…' });
        } else await this.operate('import-component', { package_text: raw }, { message: 'Component package imported with its pinned identity.' });
      } catch (error) { this.callbacks.notify(error.message, 'error'); }
      finally { input.remove(); }
    });
    input.hidden = true; document.body.append(input); input.click();
  }

  async exportEvidence(project) {
    const values = await this.form('Download private evidence package', [['confirmation', 'Type PRIVATE to continue', '']],
      'This transfer includes raw prompts, history, original host-path provenance, retained EDA files and available Functional Maps. It excludes tools, PDK and model weights. Inspect the package before sharing; it is not a public/redacted export. Missing historical files are listed explicitly. Maximum compressed size: 120 MiB.', 'Download package');
    if (values?.confirmation !== 'PRIVATE') return;
    await this.download(`workspace/evidence-export/${encodeURIComponent(itemId(project))}`, `${safe(project.name)}.hullcirq-evidence.json`);
  }

  pasteEvidence() {
    if (this.formDialog?.open) { this.formDialog.querySelector('input')?.focus(); return; }
    const dialog = el('dialog', { class: 'workspace-form-dialog', 'aria-label': 'Restore pasted evidence JSON' });
    this.formDialog = dialog;
    const name = el('input', { value: 'Restored evidence', required: true, maxlength: 160, 'aria-label': 'Restored project name' });
    const source = el('textarea', { rows: 12, required: true, spellcheck: false, 'aria-label': 'Original portable evidence JSON',
      'data-testid': 'workspace-evidence-json', style: 'width:100%' });
    const form = el('form', {}, el('h2', { text: 'Restore pasted evidence JSON' }),
      el('p', { text: 'Paste the complete original private package text, not a reformatted or rounded JSON copy. Restore creates fresh IDs and read-only archived evidence, never starts tools, and does not qualify this host. Maximum 120 MiB.' }),
      name, source, el('button', { type: 'submit', class: 'primary', text: 'Check and restore evidence', 'data-testid': 'workspace-evidence-paste-submit' }),
      this.button('Cancel', () => dialog.close()));
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const raw = source.value;
      if (raw.length > 120 * 1024 * 1024) { this.callbacks.notify('Evidence package exceeds the 120 MiB limit. No project changed.', 'error'); return; }
      const restoredName = name.value.trim();
      dialog.close();
      await this.operate('restore-evidence', { bundle_text: raw, name: restoredName }, { context: true, progress: 'Checking and restoring the raw evidence package…' });
    });
    dialog.addEventListener('close', () => { if (this.formDialog === dialog) this.formDialog = null; dialog.remove(); });
    dialog.append(form); document.body.append(dialog); dialog.showModal(); source.focus();
  }

  async inspectEvidence(project) {
    const pid = encodeURIComponent(itemId(project));
    const value = await this.callbacks.request(`workspace/evidence/${pid}`);
    const dialog = el('dialog', { class: 'workspace-form-dialog', 'aria-label': 'Verified portable evidence' });
    const rows = el('div', { 'data-testid': 'workspace-evidence-files' });
    const count = el('p', { role: 'status' });
    const search = el('input', { type: 'search', placeholder: 'Filter retained file paths', 'aria-label': 'Filter evidence files' });
    let page = 0;
    const render = () => {
      const filtered = value.entries.filter(entry => entry.path.toLowerCase().includes(search.value?.toLowerCase() || ''));
      page = Math.min(page, Math.max(0, Math.ceil(filtered.length / 100) - 1));
      rows.replaceChildren(...filtered.slice(page * 100, (page + 1) * 100).map(entry => el('p', {},
        el('code', { text: entry.path }), el('small', { text: `${entry.size} bytes · SHA-256 ${entry.sha256}` }),
        this.button('Download raw bytes', () => this.download(`workspace/evidence-file/${pid}/${entry.file_id}`, entry.path.split('/').pop())))));
      count.textContent = `${filtered.length} verified files. Page ${page + 1} / ${Math.max(1, Math.ceil(filtered.length / 100))}.`;
    };
    search.addEventListener('input', () => { page = 0; render(); });
    const mapHost = el('div');
    const mapStatus = el('p', { role: 'status', 'data-testid': 'workspace-evidence-map-status' });
    let mapViewToken = 0;
    for (const mapping of value.maps) {
      const entry = value.entries.find(item => item.path === mapping.html_path);
      mapHost.append(this.button(`Open archived Functional Map · ${mapping.layout_run_id} · ${mapping.map_id || 'static'}`, async () => {
        const token = ++mapViewToken, session = workspaceSession();
        const current = () => token === mapViewToken && dialog.open && session === workspaceSession();
        mapHost.querySelector('iframe')?.remove();
        mapStatus.textContent = 'Checking the archived map data and installed read-only viewer…';
        try {
          if (!entry) throw new Error('The archived map has no verified file entry.');
          const route = `/api/workspace/evidence-map/${pid}/${entry.file_id}`;
          const response = await sessionFetch(route, { cache: 'no-store', credentials: 'same-origin' });
          if (!current()) return;
          if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            throw new Error(body.error?.message || `Archived map could not be read (${response.status}).`);
          }
          if (!response.headers.get('content-type')?.startsWith('text/html') || !(await response.text()).trim()) throw new Error('The archived map did not return a complete HTML viewer.');
          if (!current()) return;
          mapStatus.textContent = `Verified archived map data · ${mapping.map_id || 'static'} · read-only.`;
          mapHost.append(el('iframe', { title: 'Archived read-only Functional Map', sandbox: 'allow-scripts', referrerPolicy: 'no-referrer',
            src: route, style: 'width:100%;height:65vh;border:1px solid #ccc', 'data-testid': 'workspace-evidence-map' }));
        } catch (error) {
          if (current()) mapStatus.textContent = `Failed: ${error.message || 'The archived map could not be opened.'}`;
        }
      }));
    }
    dialog.append(el('h2', { text: 'Verified portable evidence' }), el('p', { text: value.restore_policy }),
      el('p', { text: 'Raw hashes verified on this read. This is archived evidence, not a new circuit verification or host readiness check.' }),
      el('p', { text: `${value.unavailable.length} original files/maps were unavailable at export; see the manifest for the exact list.` }),
      this.button('Download verified manifest', () => this.download(`workspace/evidence/${pid}`, 'hullcirq-evidence-manifest.json')),
      mapHost, mapStatus, search, count, rows, this.button('Previous files', () => { page = Math.max(0, page - 1); render(); }),
      this.button('Next files', () => { page += 1; render(); }), this.button('Close evidence', () => dialog.close()));
    dialog.addEventListener('close', () => { mapViewToken++; dialog.remove(); });
    document.body.append(dialog); render(); dialog.showModal();
  }

  async download(path, filename) {
    try {
      const response = await sessionFetch(`/api/${path}`, { cache: 'no-store' });
      if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.error?.message || body.error || `Download failed (${response.status}).`); }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob); const link = el('a', { href: url, download: filename });
      document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { this.callbacks.notify(error.message, 'error'); }
  }

  form(title, fields, description = '', submitLabel = 'Continue') {
    // Only one command form may own focus at a time. Ignore a duplicate click
    // instead of stacking modal dialogs with the same field identities.
    if (this.formDialog?.open) { this.formDialog.querySelector('input')?.focus(); return Promise.resolve(null); }
    return new Promise(resolve => {
      const dialog = el('dialog', { class: 'workspace-form-dialog', 'aria-label': title });
      this.formDialog = dialog;
      const values = Object.fromEntries(fields.map(([id, , value]) => [id, value]));
      const inputs = new Map();
      let pickerBusy = false, settled = false;
      const status = el('p', { 'aria-live': 'polite', 'data-testid': 'workspace-folder-status' });
      const submit = el('button', { type: 'submit', class: 'primary', text: submitLabel, 'data-testid': 'workspace-form-submit' });
      const controls = fields.map(([id, label, value, options = {}]) => {
        const { folder, ...attributes } = options;
        const control = field(label, value, next => { values[id] = next; }, { id: `workspace-field-${id}`, required: true, 'data-testid': `workspace-field-${id}`, maxlength: 160, ...attributes });
        const input = control.querySelector('input'); inputs.set(id, input);
        if (folder) control.append(this.button(folder === 'parent' ? 'Choose parent folder…' : 'Browse…', async () => {
          if (pickerBusy) return;
          pickerBusy = true; submit.disabled = true; status.textContent = 'Choose a folder in the system dialog.';
          try {
            const directory = await this.pickDirectory(() => dialog.open);
            if (!dialog.open) return;
            if (directory) { values[id] = folder === 'parent' ? childDirectory(directory, values.name) : directory; input.value = values[id]; status.textContent = 'Folder selected. Review the path before continuing.'; }
            else status.textContent = 'Folder selection cancelled. You can type the path instead.';
          } catch (error) { if (dialog.open) status.textContent = error.message; }
          finally { pickerBusy = false; if (dialog.open) submit.disabled = false; }
        }, { 'data-testid': `workspace-browse-${id}` }));
        return control;
      });
      const form = el('form', { method: 'dialog' }, el('h2', { text: title }), description ? el('p', { text: description }) : null,
        ...controls, status,
        el('div', { class: 'workspace-actions' }, el('button', { type: 'button', text: 'Cancel', onclick: () => dialog.close('cancel') }), submit));
      form.addEventListener('submit', event => {
        event.preventDefault();
        if (pickerBusy || !form.reportValidity()) return;
        // Read the controls at submission as well, including autofill and
        // keyboard edits that have not emitted a change event yet.
        for (const [id, input] of inputs) values[id] = input.value;
        dialog.close('continue');
      });
      dialog.addEventListener('close', () => {
        if (settled) return;
        settled = true;
        const result = dialog.returnValue === 'continue' ? Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value.trim()])) : null;
        if (this.formDialog === dialog) this.formDialog = null;
        dialog.remove(); resolve(result);
      }, { once: true });
      dialog.append(form); document.body.append(dialog); dialog.showModal(); dialog.querySelector('input')?.focus();
    });
  }

  async pickDirectory(isOpen) {
    // The edited target may not exist yet. Do not pass it as the native
    // chooser's existing initial directory and prevent the user from browsing.
    const started = await this.callbacks.request('workspace/folder-picker', {});
    let picker = started.picker;
    if (!picker?.id) throw new Error('The folder chooser did not return a request identity. Type the folder path instead.');
    const cancel = async () => {
      if (picker.status !== 'Pending') return;
      try { await this.callbacks.request('workspace/cancel-folder-picker', { picker_id: picker.id }); }
      catch { /* A context switch also cancels the prior session's chooser. */ }
    };
    const deadline = Date.now() + 125000;
    while (picker.status === 'Pending' && isOpen()) {
      if (Date.now() >= deadline) { await cancel(); throw new Error('The folder chooser timed out. You can type the folder path instead.'); }
      await new Promise(resolve => setTimeout(resolve, 300));
      if (!isOpen()) { await cancel(); return null; }
      let result;
      try { result = await this.callbacks.request(`workspace/folder-picker/${encodeURIComponent(picker.id)}`); }
      catch (error) { await cancel(); throw error; }
      if (!result.picker?.id) { await cancel(); throw new Error('The folder chooser response was incomplete. Type the folder path instead.'); }
      picker = result.picker;
    }
    if (!isOpen()) { await cancel(); return null; }
    if (picker.status === 'Cancelled') return null;
    if (picker.status !== 'Completed' || !picker.directory) throw new Error(picker.message || (typeof picker.error === 'string' ? picker.error : picker.error?.message) || 'The system folder chooser is unavailable. Type the full folder path instead.');
    return picker.directory;
  }

  renderLegacyBackups(host) {
    const keys = ['hullcirq.m1.draft.v1', 'hullcirq.m1.recovered-drafts.v1'];
    const found = [];
    try { for (const key of keys) { const raw = localStorage.getItem(key); if (raw) found.push([key, raw]); } } catch { return; }
    if (!found.length) return;
    host.append(el('details', { class: 'workspace-legacy-backups' }, el('summary', { text: 'Earlier browser drafts are preserved' }), el('p', { text: 'These origin-wide backups predate project switching. They remain untouched and are available for download. They are never applied to another system automatically.' }),
      found.map(([key, raw]) => this.button(`Download ${key.includes('recovered') ? 'earlier recovered backups' : 'earlier draft'}`, () => {
        const blob = new Blob([raw], { type: 'application/json' }); const url = URL.createObjectURL(blob); const link = el('a', { href: url, download: `${safe(key)}.json` }); document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      }))));
  }
}
