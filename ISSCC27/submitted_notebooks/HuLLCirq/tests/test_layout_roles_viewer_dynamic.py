"""Focused software QA for the data-driven, read-only Functional Map viewer."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
TEMPLATE = ROOT / "scripts" / "templates" / "layout_roles_viewer.html"
RENDERER = ROOT / "scripts" / "render_layout_roles.py"


def load_renderer():
    spec = importlib.util.spec_from_file_location("layout_role_renderer_for_qa", RENDERER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


NODE_HARNESS = r"""
const assert = require('assert');
const vm = require('vm');
const viewerSource = __VIEWER_SOURCE__;

class ElementDouble {
  constructor(tag, id = '') {
    this.tagName = String(tag).toUpperCase(); this.id = id; this.children = []; this.listeners = {};
    this.attributes = {}; this.dataset = {}; this.style = {}; this.className = ''; this.textContent = '';
    this.hidden = false; this.disabled = false; this.checked = false; this.value = ''; this.title = '';
    this.offsetWidth = 120; this.offsetHeight = 50; this.width = 0; this.height = 0;
    this.classList = {add() {}, remove() {}};
    if (this.tagName === 'SELECT') this.options = [];
  }
  append(...nodes) {
    for (const node of nodes) {
      this.children.push(node);
      if (this.tagName === 'SELECT' && node && node.tagName === 'OPTION') this.options.push(node);
    }
  }
  replaceChildren(...nodes) {
    this.children = []; if (this.options) this.options = []; this.append(...nodes);
  }
  addEventListener(type, listener) { (this.listeners[type] ||= []).push(listener); }
  dispatch(type, values = {}) {
    const event = {target: this, currentTarget: this, key: '', button: 0, pointerId: 1,
      clientX: 0, clientY: 0, deltaY: 0, shiftKey: false, preventDefault() {}, ...values};
    for (const listener of this.listeners[type] || []) listener(event);
  }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  querySelectorAll(selector) {
    const result = [];
    const visit = node => {
      for (const child of node.children || []) {
        if (selector === 'input' && child.tagName === 'INPUT') result.push(child);
        visit(child);
      }
    };
    visit(this); return result;
  }
  getBoundingClientRect() { return {left: 0, top: 0, width: 720, height: 540}; }
  getContext(kind) {
    if (this.tagName !== 'CANVAS' || kind !== '2d') return null;
    return {setTransform() {}, fillRect() {}, strokeRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}};
  }
  focus() { this.focused = true; }
  setPointerCapture() {}
  hasPointerCapture() { return false; }
  releasePointerCapture() {}
}

const TAGS = {
  'layout-data': 'script', 'viewer-title': 'h1', 'load-error': 'div', 'loading': 'div', workspace: 'main',
  metadata: 'section', 'validation-note': 'p', 'die-label': 'div', 'source-metadata': 'pre', 'data-notes': 'ul',
  'role-list': 'div', 'status-list': 'div', 'pe-select': 'select', 'role-only-pe': 'button', 'roles-all-pe': 'button',
  'roles-all': 'button', 'roles-none': 'button', 'statuses-all': 'button', 'statuses-none': 'button',
  'layout-canvas': 'canvas', 'canvas-wrap': 'div', 'visible-count': 'span', 'view-status': 'span',
  'cell-outlines': 'input', 'selection-message': 'div', 'selection-details': 'div', 'selection-empty': 'p',
  'clear-selection': 'button', 'focus-selection': 'button', 'fit-button': 'button', 'zoom-in': 'button',
  'zoom-out': 'button', 'cell-search': 'input', 'search-results': 'div', 'search-info': 'div', 'hover-tooltip': 'div'
};

function page(payload) {
  const elements = new Map(Object.entries(TAGS).map(([id, tag]) => [id, new ElementDouble(tag, id)]));
  elements.get('layout-data').textContent = JSON.stringify(payload);
  const document = {
    title: '',
    getElementById(id) { return elements.get(id) || null; },
    createElement(tag) { return new ElementDouble(tag); }
  };
  const window = {devicePixelRatio: 1};
  const context = vm.createContext({document, window, CSS: {supports() { return true; }}, console,
    ResizeObserver: class { constructor(callback) { this.callback = callback; } observe() {} },
    requestAnimationFrame(callback) { callback(); return 1; }, setTimeout, clearTimeout});
  vm.runInContext(viewerSource, context, {filename: 'layout_roles_viewer.html'});
  const click = id => elements.get(id).dispatch('click');
  const text = node => String(node.textContent || '') + (node.children || []).map(text).join(' ');
  return {elements, window, click, text};
}

const dynamic = __DYNAMIC_PAYLOAD__;
const current = page(dynamic);
let state = current.window.HuLLCirqLayoutViewer.getState();
assert.equal(state.cellCount, 7);
assert.deepEqual(Array.from(current.elements.get('pe-select').options, option => option.value),
  ['npu2-pe00', 'npu2-pe01', 'npu2-pe10', 'npu2-pe11']);
assert.deepEqual(Array.from(current.elements.get('pe-select').options, option => option.textContent),
  ['PE 0,0 · 2 cells', 'PE 0,1 · 1 cells', 'PE 1,0 · 1 cells', 'PE 1,1 · 1 cells']);

current.click('roles-none');
state = current.window.HuLLCirqLayoutViewer.getState();
assert.deepEqual(Array.from(state.shownRoles), []); assert.equal(state.filteredCount, 0);
current.elements.get('pe-select').value = 'npu2-pe10'; current.click('role-only-pe');
state = current.window.HuLLCirqLayoutViewer.getState();
assert.deepEqual(Array.from(state.shownRoles), ['npu2-pe10']); assert.equal(state.filteredCount, 1);
current.click('roles-all-pe');
state = current.window.HuLLCirqLayoutViewer.getState();
assert.deepEqual(Array.from(state.shownRoles), ['npu2-pe00', 'npu2-pe01', 'npu2-pe10', 'npu2-pe11']);
assert.equal(state.filteredCount, 5);

current.click('roles-none');
const search = current.elements.get('cell-search'); search.value = 'cell_pe10'; search.dispatch('keydown', {key: 'Enter'});
state = current.window.HuLLCirqLayoutViewer.getState();
assert.equal(state.selectedInstance, 'cell_pe10');
assert.ok(Array.from(state.shownRoles).includes('npu2-pe10'));
assert.match(current.text(current.elements.get('selection-details')), /Supplied PE 1,0 description/);
assert.match(current.text(current.elements.get('selection-details')), /source-confirmed npu2-pe10/);

current.click('fit-button'); const fitted = current.window.HuLLCirqLayoutViewer.getState();
current.click('zoom-in'); const zoomed = current.window.HuLLCirqLayoutViewer.getState();
assert.ok(Math.abs(zoomed.scale / fitted.scale - 1.5) < 1e-9);
current.click('zoom-out'); const restoredZoom = current.window.HuLLCirqLayoutViewer.getState();
assert.ok(Math.abs(restoredZoom.scale - fitted.scale) < 1e-9);
current.elements.get('layout-canvas').dispatch('keydown', {key: 'ArrowRight'});
const panned = current.window.HuLLCirqLayoutViewer.getState();
assert.equal(panned.scale, restoredZoom.scale); assert.notEqual(panned.offsetX, restoredZoom.offsetX);
current.elements.get('layout-canvas').dispatch('keydown', {key: 'Home'});
const home = current.window.HuLLCirqLayoutViewer.getState();
assert.equal(home.scale, home.fitScale); assert.equal(home.selectedInstance, 'cell_pe10');

const legacy = page(__LEGACY_PAYLOAD__);
assert.equal(legacy.elements.get('pe-select').options.length, 16);
assert.deepEqual(Array.from(legacy.elements.get('pe-select').options, option => option.value),
  Array.from({length: 16}, (_, index) => 'pe:' + index));
legacy.click('roles-none'); legacy.click('roles-all-pe');
const legacyState = legacy.window.HuLLCirqLayoutViewer.getState();
assert.equal(legacyState.shownRoles.length, 16); assert.equal(legacyState.filteredCount, 16);

console.log(JSON.stringify({status: 'Passed', dynamic_pe_options: 4, legacy_pe_options: 16,
  filters: true, search_and_inspector: true, zoom_and_pan: true}));
"""


def payload(roles, cells):
    return {
        "schema_version": "software-qa",
        "title": "Dynamic Functional Map software QA",
        "die": [0, 0, 100, 100],
        "roles": roles,
        "cells": cells,
        "summary": {"software_qa_fixture": True},
        "provenance": {"eda_runs": 0, "model_calls": 0},
        "notes": ["Software fixture only; not physical-design evidence."],
    }


class RoleDescriptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = load_renderer()

    def test_supplied_description_is_preserved_and_new_roles_have_safe_fallbacks(self):
        supplied = "Exact saved description for the explicit four-lane dispatcher."
        self.assertEqual(self.renderer.role_description({"id": "dispatcher", "description": supplied}), supplied)
        self.assertIn("explicit PE lanes", self.renderer.role_description({"id": "dispatcher"}))
        self.assertIn("recorded output order", self.renderer.role_description({"id": "collector"}))
        self.assertIn("sixteen MAC lanes", self.renderer.role_description({"id": "scheduler"}))
        self.assertIn("RTL lane index", self.renderer.role_description({"id": "pe:15"}))
        self.assertEqual(self.renderer.role_description({"id": "future-role"}), "No role description supplied.")


class DynamicViewerTests(unittest.TestCase):
    def test_category_notes_are_project_neutral_and_do_not_assert_pe_ownership(self):
        source = TEMPLATE.read_text(encoding='utf-8')
        self.assertIn('never silently assigned to a functional role', source)
        self.assertIn('distinct from functional block roles', source)
        self.assertNotIn('never silently assigned to a PE', source)
        self.assertNotIn('functional PE ownership', source)

    def test_dynamic_four_pe_controls_and_legacy_sixteen_pe_compatibility(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for the isolated viewer regression.")
        template = TEMPLATE.read_text(encoding="utf-8")
        executable = re.findall(r"<script>(.*?)</script\s*>", template, re.S | re.I)
        self.assertEqual(len(executable), 1)
        viewer = executable[0].replace("/*__LAYOUT_UNPACK__*/", "const unpackLayoutData = value => value;")

        dynamic_roles = [
            {"id": "control", "label": "Job control", "color": "#f97316", "description": "Supplied control description."},
            *[
                {"id": f"npu2-pe{name}", "label": f"PE {name[0]},{name[1]}", "group": "pe",
                 "color": "#2563eb", "description": f"Supplied PE {name[0]},{name[1]} description."}
                for name in ("00", "01", "10", "11")
            ],
            {"id": "physical", "label": "Physical support", "color": "#cbd5e1", "description": "Physical support."},
        ]
        dynamic_cells = [
            {"id": "cell_control", "master": "buf_1", "bbox": [2, 2, 5, 5], "role": "control",
             "status": "source_confirmed", "evidence": ["source-confirmed control"]},
            {"id": "cell_pe00_a", "master": "buf_1", "bbox": [10, 10, 13, 13], "role": "npu2-pe00",
             "status": "source_confirmed", "evidence": ["source-confirmed npu2-pe00"]},
            {"id": "cell_pe00_b", "master": "buf_1", "bbox": [14, 10, 17, 13], "role": "npu2-pe00",
             "status": "source_confirmed", "evidence": ["source-confirmed npu2-pe00"]},
            *[
                {"id": f"cell_pe{name}", "master": "buf_1", "bbox": [x, 20, x + 3, 23],
                 "role": f"npu2-pe{name}", "status": "source_confirmed",
                 "evidence": [f"source-confirmed npu2-pe{name}"]}
                for name, x in (("01", 20), ("10", 30), ("11", 40))
            ],
            {"id": "fill", "master": "fill_1", "bbox": [50, 50, 53, 53], "role": "physical",
             "status": "physical_inferred", "evidence": ["physical support"]},
        ]
        legacy_roles = [
            {"id": f"pe:{index}", "label": f"PE {index}", "color": "#2563eb", "description": "Legacy PE."}
            for index in range(16)
        ]
        legacy_cells = [
            {"id": f"legacy_{index}", "master": "buf_1", "bbox": [index * 4, 2, index * 4 + 2, 4],
             "role": f"pe:{index}", "status": "source_and_connectivity", "evidence": ["legacy"]}
            for index in range(16)
        ]
        source = (NODE_HARNESS
                  .replace("__VIEWER_SOURCE__", json.dumps(viewer))
                  .replace("__DYNAMIC_PAYLOAD__", json.dumps(payload(dynamic_roles, dynamic_cells)))
                  .replace("__LEGACY_PAYLOAD__", json.dumps(payload(legacy_roles, legacy_cells))))
        result = subprocess.run([node, "-"], input=source, cwd=ROOT, capture_output=True,
                                text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(report["status"], "Passed")
        self.assertEqual(report["dynamic_pe_options"], 4)
        self.assertEqual(report["legacy_pe_options"], 16)


if __name__ == "__main__":
    unittest.main()
