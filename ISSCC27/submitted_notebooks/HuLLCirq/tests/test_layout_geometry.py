"""Isolated footprint-reader checks; the real NPU binding is recorded separately."""

from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hullcirq.layout_geometry import bind_def_geometry, read_gds_footprints, reference_bbox


class LayoutGeometryTests(unittest.TestCase):
    def test_gds_reflection_and_rotation_keep_actual_footprint_origin(self):
        self.assertEqual(reference_bbox([0, 0, 10, 20], [50, 70], reflected=True), [50, 50, 60, 70])
        self.assertEqual(reference_bbox([0, 0, 10, 20], [50, 70], angle=180), [40, 50, 50, 70])
        self.assertEqual(reference_bbox([0, 0, 10, 20], [50, 70], angle=180, reflected=True), [40, 70, 50, 90])
        self.assertEqual(reference_bbox([0, 0, 10, 20], [50, 70], angle=90), [30, 70, 50, 80])

    def test_unsupported_transforms_fail_instead_of_drawing_guessed_geometry(self):
        for kwargs in ({"angle": 30}, {"magnification": 2}):
            with self.assertRaises(ValueError):
                reference_bbox([0, 0, 10, 20], [0, 0], **kwargs)

    def test_truncated_gds_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "truncated.gds"
            p.write_bytes(struct.pack(">HBB", 20, 3, 5) + b"\0" * 4)
            with self.assertRaisesRegex(ValueError, "truncated"):
                read_gds_footprints(p)

    def _bind(self, component, gds):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "sample.def"
            p.write_text("UNITS DISTANCE MICRONS 1000 ;\nDIEAREA ( 0 0 ) ( 10000 10000 ) ;\nCOMPONENTS 1 ;\n" + component + "\nEND COMPONENTS\n", encoding="utf-8")
            return bind_def_geometry(p, gds)

    def test_def_matches_named_gds_boundary_not_routing_bbox(self):
        result = self._bind("- placed master + PLACED ( 1000 2000 ) FS ;", {"cells": {"placed": {"master": "master", "bbox": [1, 2, 3, 4]}}})
        self.assertEqual(result["die"], [0, 0, 10, 10])
        self.assertEqual(result["component_count"], 1)

    def test_identity_origin_or_count_mismatch_fails(self):
        for cells in ({"placed": {"master": "different", "bbox": [1, 2, 3, 4]}},
                      {"placed": {"master": "master", "bbox": [1, 2.1, 3, 4]}},
                      {"placed": {"master": "master", "bbox": [1, 2, 3, 4]}, "extra": {"master": "master", "bbox": [1, 2, 3, 4]}}):
            with self.assertRaises(ValueError):
                self._bind("- placed master + PLACED ( 1000 2000 ) N ;", {"cells": cells})


if __name__ == "__main__":
    unittest.main()
