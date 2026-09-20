#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]
SCRIPT = SKILL_DIR / "scripts" / "cad_municipal_geometry.py"


class MunicipalGeometryTest(unittest.TestCase):
    def run_script(self, detail: dict, out_name: str = "out") -> tuple[dict, Path]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        src = root / "detail.json"
        src.write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")
        out = root / out_name
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(src), "--out-dir", str(out)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads((out / "detail.municipal.json").read_text(encoding="utf-8")), out

    def test_extracts_municipal_roads_pipes_bridges_materials_and_labels(self):
        detail = {
            "meta": {"sheets": [{"id": 1, "bbox": [0, 0, 10000, 10000]}]},
            "files": [{"name": "generic-municipal.dwg"}],
            "text_records": [
                {"kind": "TEXT", "text": "市政道路工程平面图 1:1000 单位：m", "layer": "TITLE", "x": 100, "y": 9900, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "道路中线 K0+000", "layer": "ROAD-CENTER", "x": 1000, "y": 1000, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "路缘石 花岗岩", "layer": "ROAD-KERB", "x": 1100, "y": 1000, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "雨水管 DN600", "layer": "DRAIN-STORM", "x": 2000, "y": 1000, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "检查井 700", "layer": "DRAIN-MANHOLE", "x": 2100, "y": 1000, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "桥墩 C35", "layer": "BRIDGE-PIER", "x": 3000, "y": 1000, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "箱梁 C50", "layer": "BRIDGE-GIRDER", "x": 3100, "y": 1000, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "路面结构 4cm AC-13 + 6cm AC-20", "layer": "PAVEMENT", "x": 4000, "y": 1000, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "标高 12.500", "layer": "LEVEL", "x": 100, "y": 200, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "X=100.000 Y=200.000", "layer": "COORD", "x": 100, "y": 300, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "i=0.003", "layer": "ROAD-PROFILE", "x": 100, "y": 400, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "GB 50010", "layer": "NOTE", "x": 100, "y": 500, "sheet": 1, "file": 0},
            ],
            "geometry_segments": [[
                [0, 0, 100, 0], [100, 0, 100, 50], [100, 50, 0, 50], [0, 50, 0, 0]
            ]],
            "geometry_layers": [["ROAD-道路中线", "DRAIN-检查井", "BRIDGE-桥墩", "ROAD-道路中线"]],
        }
        result, out = self.run_script(detail)
        self.assertEqual(result["schema"], "cad-municipal-geometry/v1")
        self.assertGreaterEqual(result["summary"]["drawing_types"], 2)
        self.assertGreaterEqual(result["summary"]["systems"], 3)
        self.assertGreaterEqual(result["summary"]["components"], 5)
        self.assertGreaterEqual(result["summary"]["pipe_candidates"], 1)
        self.assertGreaterEqual(result["summary"]["materials"], 3)
        self.assertGreaterEqual(result["summary"]["labels"], 4)
        self.assertEqual(result["summary"]["geometry_segments"], 4)
        categories = {row["category"] for row in result["components"]}
        self.assertIn("road_centerline", categories)
        self.assertIn("kerb", categories)
        self.assertIn("manhole", categories)
        self.assertIn("bridge_pier", categories)
        self.assertIn("girder", categories)
        self.assertEqual(result["pipe_network"][0]["pipe_size"], "DN600")
        self.assertIn("不输出面积", result["boundary"])
        self.assertNotIn("quantity", result)
        self.assertTrue((out / "detail.municipal.md").exists())
        self.assertTrue((out / "detail.municipal.csv").exists())

    def test_missing_scale_and_geometry_enter_review(self):
        detail = {
            "meta": {"sheets": [{"id": 1, "bbox": [0, 0, 1000, 1000]}]},
            "files": [{"name": "municipal.dwg"}],
            "text_records": [
                {"kind": "TEXT", "text": "市政道路工程平面图 单位：m", "layer": "TITLE", "x": 10, "y": 10, "sheet": 1, "file": 0},
            ],
        }
        result, _out = self.run_script(detail)
        review_types = {row["type"] for row in result["review"]}
        self.assertIn("scale_unit", review_types)
        self.assertIn("input_geometry", review_types)
        self.assertEqual(result["summary"]["geometry_segments"], 0)

    def test_connectivity_marks_isolated_municipal_segment(self):
        detail = {
            "meta": {"sheets": [{"id": 1, "bbox": [0, 0, 1000, 1000]}]},
            "files": [{"name": "municipal.dwg"}],
            "text_records": [],
            "geometry_segments": [[[0, 0, 100, 0]]],
            "geometry_layers": [["ROAD-道路中线"]],
        }
        result, _out = self.run_script(detail)
        self.assertEqual(result["connectivity"]["summary"]["open_endpoints"], 2)
        self.assertEqual(result["connectivity"]["summary"]["isolated_segments"], 1)


if __name__ == "__main__":
    unittest.main()
