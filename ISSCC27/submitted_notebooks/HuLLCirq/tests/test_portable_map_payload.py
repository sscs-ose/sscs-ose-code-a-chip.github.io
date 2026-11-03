"""Archived producer-format Map data uses installed code, never imported JS."""
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from hullcirq.domain import DomainError
from hullcirq.layout_role_view import functional_map_csp
from hullcirq.portable_projects import map_view_bytes
from render_layout_roles import packed_payload


class PortableMapPayloadTests(unittest.TestCase):
    def payload(self):
        return {"die": [0, 0, 10, 10], "roles": [{"id": "logic", "label": "Logic"}],
                "cells": [{"id": "cell0", "master": "master0", "bbox": [1, 2, 3, 4],
                           "role": "logic", "status": "source_confirmed", "evidence": ["saved evidence <tag>"]}]}

    def archive(self, payload):
        # Deliberately imported executable script must not reach rebuilt HTML.
        encoded = json.dumps(payload, ensure_ascii=True).replace("<", "\\u003c")
        return ('<script id="layout-data" type="application/json">' + encoded + '</script>'
                '<script>globalThis.importedArchiveScriptRan = true;</script>').encode()

    def render(self, payload):
        raw = self.archive(payload)
        with patch("hullcirq.portable_projects.artifact_bytes", return_value=(raw, {
                "kind": "functional_map", "path": "maps/s/r/v/view/layout_roles.html"})):
            return map_view_bytes(None, "software-qa-only", "0"), raw

    def test_real_producer_packed_payload_is_rebuilt_with_only_installed_decoder(self):
        original = self.payload()
        packed = packed_payload(copy.deepcopy(original))
        self.assertNotIn("cells", packed)
        rebuilt, raw = self.render(packed)
        self.assertNotIn(b"importedArchiveScriptRan", rebuilt)
        self.assertIn(b"importedArchiveScriptRan", raw)
        self.assertNotIn(b"/*__LAYOUT_UNPACK__*/", rebuilt)
        self.assertIn((ROOT / "scripts/templates/layout_roles_unpack.js").read_bytes().rstrip(), rebuilt)
        match = re.search(rb'<script id="layout-data" type="application/json">(.*?)</script>', rebuilt, re.S)
        self.assertEqual(json.loads(match[1]), packed)
        self.assertIn("script-src 'sha256-", functional_map_csp(rebuilt))
        self.assertIn("connect-src 'none'", functional_map_csp(rebuilt))
        node = shutil.which("node")
        if node:
            decoder = (ROOT / "scripts/templates/layout_roles_unpack.js").read_text(encoding="utf-8")
            script = decoder + "\nprocess.stdout.write(JSON.stringify(unpackLayoutData(" + json.dumps(packed) + ")));"
            result = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            decoded = json.loads(result.stdout)
            self.assertEqual(decoded["cells"], original["cells"])
            self.assertEqual(decoded["die"], original["die"])
            self.assertNotIn("strings", decoded)
            self.assertNotIn("cell_rows", decoded)

    def test_plain_legacy_payload_remains_plain_and_imported_script_is_not_used(self):
        value = self.payload()
        rebuilt, _ = self.render(value)
        self.assertNotIn(b"importedArchiveScriptRan", rebuilt)
        match = re.search(rb'<script id="layout-data" type="application/json">(.*?)</script>', rebuilt, re.S)
        self.assertEqual(json.loads(match[1]), value)

    def test_invalid_encoding_indices_rows_and_bounds_are_rejected(self):
        original = packed_payload(self.payload())
        invalid = []
        for change in (
            lambda p: p.update(cell_encoding="unknown-v2"),
            lambda p: p.update(cells=[]),
            lambda p: p.update(strings={}),
            lambda p: p.update(cell_rows={}),
            lambda p: p["strings"].append({"not": "text"}),
            lambda p: p["cell_rows"].append([]),
            lambda p: p["cell_rows"][0].__setitem__(0, True),
            lambda p: p["cell_rows"][0].__setitem__(1, -1),
            lambda p: p["cell_rows"][0].__setitem__(3, len(p["strings"])),
            lambda p: p["cell_rows"][0].__setitem__(4, "0"),
            lambda p: p["cell_rows"][0].__setitem__(5, [-1]),
            lambda p: p["cell_rows"][0].__setitem__(5, {}),
            lambda p: p["cell_rows"][0].__setitem__(2, [1, 2, 0, 4]),
            lambda p: p["cell_rows"][0].__setitem__(2, [0, 0, True, 4]),
            lambda p: p["cell_rows"][0].__setitem__(2, [0, 0, 1 << 2048, 4]),
        ):
            candidate = copy.deepcopy(original)
            change(candidate)
            invalid.append(candidate)
        for index, candidate in enumerate(invalid):
            with self.subTest(index=index), self.assertRaises(DomainError):
                self.render(candidate)


if __name__ == "__main__":
    unittest.main()
