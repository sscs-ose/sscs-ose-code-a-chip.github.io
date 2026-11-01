"""Public fresh compiler path support retains complete package verification."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hullcirq import postroute_tools as tools
from hullcirq.domain import DomainError


class FreshCompilerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'.work/qa')
        self.addCleanup(temp.cleanup); self.root = Path(temp.name).resolve()
        self.scope = self.root/'.work/fresh/0123456789ab'; self.scope.mkdir(parents=True)
        self.compiler = dict(kind='wsl', distribution='Ubuntu', executable='ROOT/usr/bin/iverilog',
            base_directory='ROOT/usr/lib/x86_64-linux-gnu/ivl', working_directory=str(self.scope/'syntax'))
        (self.scope/'compiler.json').write_text(json.dumps(self.compiler), encoding='utf-8')

    def test_fresh_route_is_exact_host_scope_and_requires_its_saved_configuration(self):
        expected = self.scope/'iverilog'
        def native(value):
            return expected/str(value)[len('ROOT/'): ] if value.startswith('ROOT/') else expected
        with patch.object(tools,'ROOT',self.root), patch.object(tools,'_native_wsl_path',side_effect=native):
            self.assertEqual(tools._compiler_root(self.compiler),expected)
            changed = {**self.compiler,'working_directory':str(self.root/'elsewhere')}
            with self.assertRaises(DomainError): tools._compiler_root(changed)
            (self.scope/'compiler.json').write_text('{}',encoding='utf-8')
            with self.assertRaises(DomainError): tools._compiler_root(self.compiler)

    def test_arbitrary_unrecognized_scope_is_rejected(self):
        with patch.object(tools,'ROOT',self.root), patch.object(tools,'_native_wsl_path',return_value=self.root/'.work/fresh/arbitrary/iverilog'):
            with self.assertRaises(DomainError): tools._compiler_root(self.compiler)

    def test_fresh_package_must_be_present_and_pinned_in_downloads(self):
        manifest = tools._compiler_package_manifest()
        with patch.object(tools,'ROOT',self.root), patch.object(tools,'_compiler_package_manifest',return_value=manifest):
            with self.assertRaises(DomainError): tools._verified_compiler_inventory(self.scope/'iverilog')
