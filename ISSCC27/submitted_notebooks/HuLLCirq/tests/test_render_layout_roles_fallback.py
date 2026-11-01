"""Focused QA for the dependency-free Functional Map PNG renderer."""
from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest import mock
import zlib


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
RENDERER = ROOT / "scripts" / "render_layout_roles.py"


def load_renderer():
    spec = importlib.util.spec_from_file_location("layout_role_png_renderer_for_qa", RENDERER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def parse_png(payload):
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError("PNG signature is missing")
    chunks = []
    cursor = 8
    while cursor < len(payload):
        length = struct.unpack(">I", payload[cursor:cursor + 4])[0]
        kind = payload[cursor + 4:cursor + 8]
        data = payload[cursor + 8:cursor + 8 + length]
        crc = struct.unpack(">I", payload[cursor + 8 + length:cursor + 12 + length])[0]
        if crc != zlib.crc32(kind + data) & 0xFFFFFFFF:
            raise AssertionError(f"Invalid {kind!r} CRC")
        chunks.append((kind, data))
        cursor += 12 + length
        if kind == b"IEND":
            break
    if cursor != len(payload):
        raise AssertionError("Trailing or truncated PNG data")
    return chunks


def fixture_data():
    return {
        "die": [0.0, 0.0, 100.0, 80.0],
        "roles": [
            {"id": "control", "label": "Control", "color": "#e53935"},
            {"id": "pe:0", "label": "PE 00", "color": "#1e88e5"},
            {"id": "physical", "label": "Physical", "color": "#90a4ae"},
            {"id": "unknown", "label": "Unknown", "color": "#7a8494"},
        ],
        "cells": [
            {"id": "u_control", "role": "control", "bbox": [10.0, 10.0, 20.0, 20.0]},
            {"id": "u_pe00", "role": "pe:0", "bbox": [60.0, 40.0, 80.0, 60.0]},
            {"id": "u_fill", "role": "physical", "bbox": [0.0, 0.0, 5.0, 80.0]},
        ],
    }


class StdlibPngFallbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = load_renderer()

    def render_without_pillow(self, destination):
        real_import = builtins.__import__

        def import_without_pillow(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "PIL" or name.startswith("PIL."):
                raise ModuleNotFoundError("Pillow deliberately unavailable in fallback QA", name=name)
            return real_import(name, globals, locals, fromlist, level)

        with mock.patch("builtins.__import__", side_effect=import_without_pillow):
            self.renderer.draw_figure(fixture_data(), destination)

    def test_missing_pillow_produces_deterministic_evidence_png(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.png"
            second = Path(temporary) / "second.png"
            self.render_without_pillow(first)
            self.render_without_pillow(second)
            payload = first.read_bytes()
            repeated_payload = second.read_bytes()

        self.assertEqual(payload, repeated_payload)
        chunks = parse_png(payload)
        ihdr = next(data for kind, data in chunks if kind == b"IHDR")
        self.assertEqual(struct.unpack(">II", ihdr[:8]), (2300, 1800))
        self.assertEqual(ihdr[8:13], bytes((8, 2, 0, 0, 0)))
        metadata = {}
        for kind, value in chunks:
            if kind == b"tEXt":
                key, text = value.split(b"\0", 1)
                metadata[key.decode("latin-1")] = text.decode("latin-1")
        self.assertEqual(metadata["Renderer"], "Python standard library deterministic fallback")
        self.assertEqual(metadata["CellCount"], "3")
        self.assertEqual(metadata["RoleCounts"], "control=1;pe:0=1;physical=1")

        compressed = b"".join(data for kind, data in chunks if kind == b"IDAT")
        raster = zlib.decompress(compressed)
        stride = 2300 * 3 + 1
        self.assertEqual(len(raster), stride * 1800)
        self.assertTrue(all(raster[row * stride] == 0 for row in range(1800)))

        def pixel(x, y):
            start = y * stride + 1 + x * 3
            return tuple(raster[start:start + 3])

        # Samples inside the actual transformed placement rectangles.
        self.assertEqual(pixel(300, 1500), (0xE5, 0x39, 0x35))
        self.assertEqual(pixel(1100, 950), (0x1E, 0x88, 0xE5))
        self.assertEqual(pixel(100, 1000), (0xE6, 0xE9, 0xEF))
        # Legend bands carry the same per-role colors and are not a blank snapshot.
        self.assertEqual(pixel(1800, 240), (0xE5, 0x39, 0x35))
        self.assertEqual(pixel(1800, 283), (0x1E, 0x88, 0xE5))
        self.assertEqual(pixel(1800, 326), (0xE6, 0xE9, 0xEF))
        self.assertGreater(len(set(payload)), 40)

    def test_pillow_availability_keeps_existing_renderer_path(self):
        fake_pillow = types.ModuleType("PIL")
        with mock.patch.dict(sys.modules, {"PIL": fake_pillow}):
            with mock.patch.object(self.renderer, "_draw_figure_pillow") as pillow_renderer:
                self.renderer.draw_figure(fixture_data(), Path("unused.png"))
        pillow_renderer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
