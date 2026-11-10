#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结构块几何展开回归：合成 DXF 的基点、嵌套变换与输出字段。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _fixture_common as common  # noqa: E402

common.ensure_runtime()
common.prepare_paths()


def _close(actual, expected, tol=1e-6):
    return all(abs(float(a) - float(e)) <= tol for a, e in zip(actual, expected))


class StructuralEquivalenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cad-struct-test-")
        cls.base = Path(cls.tmp.name)
        cls.dxf = cls.base / "fixture.dxf"
        common.make_fixture(cls.dxf)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_block_geometry_and_structural_transform(self):
        detail = self.base / "detail.json"
        scan_out = self.base / "scan.json"
        subprocess.run(
            [sys.executable, str(common.SCRIPTS / "cad_scan.py"), str(self.dxf),
             "--with-block-expand", "--detail-json", str(detail), "-o", str(scan_out)],
            check=True, capture_output=True, text=True,
        )
        data = json.loads(detail.read_text(encoding="utf-8"))
        entries = data["block_geometry"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(len(entry["segments"]), 10)
        blocks = {row["block_name"]: row for row in entry["blocks"] if row.get("source") == "dxf_block_definition"}
        self.assertEqual(blocks["BLK-A"]["base_point"], [100.0, 50.0])
        self.assertEqual(blocks["BLK-B"]["base_point"], [0.0, 0.0])

        segs = entry["segments"]
        top_a = next(r for r in segs if r["source_block"] == "BLK-A" and r.get("kind") == "LINE")
        nested = next(r for r in segs if r["source_block"] == "BLK-B/BLK-A" and r.get("kind") == "LINE")
        self.assertTrue(_close(top_a["geometry"], [1135.705081, 164.951905, 1482.115242, 364.951905]))
        self.assertTrue(_close(nested["geometry"], [450.0, 600.0, 450.0, 800.0]))
        self.assertTrue(all(r.get("handle") is not None for r in segs))

        out_dir = self.base / "structural"
        subprocess.run(
            [sys.executable, str(common.SCRIPTS / "cad_structural_geometry.py"), str(detail), "--out-dir", str(out_dir)],
            check=True, capture_output=True, text=True,
        )
        payload = json.loads((out_dir / "detail.structural.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["structural_geometry"], 10)
        self.assertEqual(payload["summary"]["raw_geometry"], 10)
        self.assertEqual(payload["summary"]["blocks"], 8)
        self.assertEqual(payload["units"]["drawing_unit"], "m")
        rows = payload["structural_geometry"]
        self.assertTrue(all(r["category"] == "raw_geometry" for r in rows))
        self.assertTrue(all(r["source"].startswith("block:") or r["source"] == "modelspace" for r in rows))
        self.assertTrue(_close(rows[1]["geometry"], [1135.705081, 164.951905, 1482.115242, 364.951905]))

    def test_without_block_expand_is_reviewed_not_faked(self):
        detail = self.base / "detail_noblock.json"
        scan_out = self.base / "scan_noblock.json"
        subprocess.run(
            [sys.executable, str(common.SCRIPTS / "cad_scan.py"), str(self.dxf), "--detail-json", str(detail), "-o", str(scan_out)],
            check=True, capture_output=True, text=True,
        )
        out_dir = self.base / "structural_noblock"
        subprocess.run(
            [sys.executable, str(common.SCRIPTS / "cad_structural_geometry.py"), str(detail), "--out-dir", str(out_dir)],
            check=True, capture_output=True, text=True,
        )
        payload = json.loads((out_dir / "detail_noblock.structural.json").read_text(encoding="utf-8"))
        types = [r.get("type", "") for r in payload.get("review", [])]
        self.assertIn("block_geometry_unavailable", types)
        self.assertEqual(payload["summary"]["raw_geometry"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
