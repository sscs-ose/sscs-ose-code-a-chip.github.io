"""Isolated SOFTWARE QA for portable admission; no actual layout/model call."""
from __future__ import annotations

import copy
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

from replay_physical_proof import archive_path, decode_prior, expected_config, old_wsl_path, replay, verify_files
from collect_physical_proof import digest
from hullcirq.domain import DomainError


class PhysicalReplayTests(unittest.TestCase):
    def test_portable_raw_bytes_hashes_and_strict_paths_do_not_need_old_machine_files(self):
        with tempfile.TemporaryDirectory(prefix="portable-physical-software-qa-") as name:
            folder = Path(name); raw = b"SOFTWARE QA ONLY\r\n\x00\xff"; (folder / "raw.bin").write_bytes(raw)
            entry = {"sha256": digest(raw), "bytes": len(raw)}
            verify_files(folder, {"raw.bin": entry})
            for relative in ("../raw.bin", "./raw.bin", "/raw.bin", "C:/old/raw.bin", "a/../raw.bin", "a\\raw.bin"):
                with self.subTest(relative=relative), self.assertRaises(ValueError): archive_path(folder, relative)
            for changed in ({"bytes": True}, {"sha256": "0" * 64}, {"bytes": len(raw) - 1}):
                with self.subTest(changed=changed), self.assertRaises(ValueError): verify_files(folder, {"raw.bin": {**entry, **changed}})
            (folder / "raw.bin").write_bytes(raw.replace(b"\r\n", b"\n"))
            with self.assertRaises(ValueError): verify_files(folder, {"raw.bin": entry})

    def test_archival_windows_to_WSL_conversion_is_lexical_and_path_independent(self):
        with patch.object(Path, "resolve", side_effect=AssertionError("Must not resolve original machine paths")):
            self.assertEqual(old_wsl_path(r"C:\not-installed\prior machine\run"), "/mnt/c/not-installed/prior machine/run")
            self.assertEqual(old_wsl_path("/mnt/d/old-machine/run"), "/mnt/d/old-machine/run")
            for value in ("relative/run", r"\\server\share\run", "C:/old\nrun"):
                with self.subTest(value=value), self.assertRaises(ValueError): old_wsl_path(value)

    def test_prior_history_expansion_is_lossless_typed_and_bounded(self):
        with tempfile.TemporaryDirectory(prefix="portable-physical-software-qa-") as name:
            folder = Path(name); raw = b'{"SOFTWARE_QA_ONLY":true,"wide":18446744073709551615}\r\n'
            archive = gzip.compress(raw, mtime=0); (folder / "history.json.gz").write_bytes(archive)
            descriptor = {"archive": "history.json.gz", "compression": "gzip", "archive_sha256": digest(archive), "archive_bytes": len(archive),
                "decompressed_sha256": digest(raw), "decompressed_bytes": len(raw)}
            self.assertEqual(decode_prior(folder, "", descriptor)[0], raw)
            for changed in ({"decompressed_bytes": True}, {"decompressed_bytes": len(raw) - 1}, {"archive_bytes": True},
                    {"decompressed_sha256": "0" * 64}, {"archive": "../history.json.gz"}):
                with self.subTest(changed=changed), self.assertRaises(ValueError): decode_prior(folder, "", {**descriptor, **changed})

    def test_failed_archive_admission_happens_before_runtime_read_or_tool_start(self):
        scratch = ROOT / ".work/software-qa-physical-replay"; scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="rejected-", dir=scratch) as name:
            output = Path(name) / "fresh-output"
            with patch("replay_physical_proof.inspect_evidence", side_effect=ValueError("SOFTWARE QA changed source")), \
                    patch("hullcirq.physical_tools.run_layout") as runner:
                with self.assertRaises(ValueError): replay(Path(name) / "unavailable-archive", Path(name) / "unavailable-runtime", output)
                runner.assert_not_called(); self.assertFalse(output.exists())

    def test_unpinned_new_runtime_and_unsafe_output_reject_before_tool_start(self):
        scratch = ROOT / ".work/software-qa-physical-replay"; scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="rejected-", dir=scratch) as name:
            root = Path(name); evidence = root / "archive"; evidence.mkdir(); (evidence / "manifest.json").write_bytes(b"{}")
            config = root / "runtime.json"; config.write_bytes(b'{"kind":"wsl","release":"wrong","SOFTWARE_QA_ONLY":true}')
            original = {"settings": {"top_module": "software_qa"}}
            with patch("replay_physical_proof.inspect_evidence", return_value=({}, original)), patch("hullcirq.physical_tools.run_layout") as runner:
                with self.assertRaises(DomainError): replay(evidence, config, root / "new-output")
                runner.assert_not_called(); self.assertFalse((root / "new-output").exists())
                with self.assertRaises(ValueError): replay(evidence, config, evidence)
                runner.assert_not_called()


if __name__ == "__main__": unittest.main()
