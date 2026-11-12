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
SCRIPT = SKILL_DIR / "scripts" / "cad_site_geometry.py"


class SiteGeometryTest(unittest.TestCase):
    def run_script(self, detail, out_name="out", extra_args=None, cwd=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        src = root / "detail.json"
        src.write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")
        out = root / out_name
        argv = [sys.executable, str(SCRIPT), str(src), "--out-dir", str(out)] + list(extra_args or [])
        proc = subprocess.run(argv, capture_output=True, text=True, cwd=str(cwd or root))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads((out / "detail.site.json").read_text(encoding="utf-8")), out

    def test_extracts_site_components_references_and_geometry(self):
        detail = {
            "meta": {"sheets": [{"id": 1, "bbox": [0, 0, 100000, 100000]}]},
            "files": [{"name": "site.dwg"}],
            "text_records": [
                {"kind": "TEXT", "text": "总平面图 1:500 单位：mm", "layer": "TITLE", "x": 1000, "y": 99000, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "用地红线 场地边界", "layer": "SITE-BOUNDARY", "x": 10000, "y": 10000, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "挡土墙 护坡", "layer": "RETAINING", "x": 20000, "y": 20000, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "标高 5.500 挖方", "layer": "ELEV", "x": 30000, "y": 30000, "sheet": 1, "file": 0},
                {"kind": "TEXT", "text": "K1+200 X=123.45 Y=678.90", "layer": "REF", "x": 40000, "y": 40000, "sheet": 1, "file": 0},
            ],
            "geometry_segments": [[
                [0, 0, 50000, 0],
                [50000, 0, 50000, 50000],
                [0, 10000, 10000, 10000],
            ]],
            "geometry_layers": [["SITE-道路", "SITE-挡土墙", "0-建筑-屋顶-外轮廓_03_小"]],
        }
        result, out = self.run_script(detail)
        self.assertEqual(result["schema"], "cad-site-geometry/v1")
        self.assertGreaterEqual(result["summary"]["drawing_types"], 1)
        self.assertGreaterEqual(result["summary"]["systems"], 1)
        self.assertGreaterEqual(result["summary"]["components"], 1)
        self.assertGreaterEqual(result["summary"]["references"], 1)
        self.assertEqual(result["summary"]["site_geometry"], 3)
        self.assertEqual(
            [row["category"] for row in result["site_geometry"]],
            ["road", "retaining_wall", "building_outline"],
        )
        self.assertIn("不输出土方量", result["boundary"])
        categories = {row["category"] for row in result["components"]}
        self.assertTrue(categories & {"site_boundary", "retaining_wall"})
        self.assertTrue((out / "detail.site.md").exists())
        self.assertTrue((out / "detail.site.csv").exists())
        contract = result["contract"]
        sections = {row["section"] for row in contract["candidates"] + contract["review_candidates"]}
        self.assertTrue(sections & {"components", "references", "site_geometry"})

    def test_source_drawing_hash_is_attached_to_contract(self):
        detail = {
            "meta": {"sheets": [{"id": 1, "bbox": [0, 0, 1000, 1000]}]},
            "files": [{"name": "site.dwg"}],
            "text_records": [{"kind": "TEXT", "text": "总平面 单位：mm", "layer": "TITLE", "x": 10, "y": 10, "sheet": 1, "file": 0}],
        }
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        drawing = Path(temp.name) / "site.dwg"
        drawing.write_bytes(b"real drawing bytes for hash regression")
        result, _out = self.run_script(detail, extra_args=["--source-drawing", str(drawing)])
        import hashlib
        expected = hashlib.sha256(drawing.read_bytes()).hexdigest()
        self.assertEqual(result["contract"]["source_sha256"], expected)
        self.assertEqual(result["contract"]["source_sha256_reason"], "computed")

    def test_explicit_source_drawing_wins_over_same_name_input(self):
        """从详情 JSON 所在目录运行时，detail.json 不得混进原图哈希。"""
        detail = {
            "meta": {"sheets": [{"id": 1, "bbox": [0, 0, 1000, 1000]}]},
            "files": [{"name": "site.dwg"}],
            "text_records": [{"kind": "TEXT", "text": "总平面 单位：mm", "layer": "TITLE", "x": 10, "y": 10, "sheet": 1, "file": 0}],
        }
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        drawing = Path(temp.name) / "site.dwg"
        drawing.write_bytes(b"explicit drawing wins")
        root = Path(temp.name)
        # cwd 里存在 detail.json，旧实现会把它和原图一起算成 computed_bundle。
        result, _out = self.run_script(detail, extra_args=["--source-drawing", str(drawing)], cwd=root)
        import hashlib
        self.assertEqual(result["contract"]["source_sha256"], hashlib.sha256(drawing.read_bytes()).hexdigest())
        self.assertEqual(result["contract"]["source_sha256_reason"], "computed")

    def test_missing_explicit_source_drawing_does_not_guess(self):
        detail = {
            "meta": {"sheets": [{"id": 1, "bbox": [0, 0, 1000, 1000]}]},
            "files": [{"name": "site.dwg"}],
            "text_records": [{"kind": "TEXT", "text": "总平面 单位：mm", "layer": "TITLE", "x": 10, "y": 10, "sheet": 1, "file": 0}],
        }
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        result, _out = self.run_script(detail, extra_args=["--source-drawing", str(root / "missing.dwg")], cwd=root)
        self.assertIsNone(result["contract"]["source_sha256"])
        self.assertEqual(result["contract"]["source_sha256_reason"], "source_not_found")

    def test_missing_scale_and_geometry_enter_review(self):
        detail = {
            "meta": {"sheets": [{"id": 1, "bbox": [0, 0, 1000, 1000]}]},
            "files": [{"name": "site.dwg"}],
            "text_records": [{"kind": "TEXT", "text": "总平面 单位：mm", "layer": "TITLE", "x": 10, "y": 10, "sheet": 1, "file": 0}],
        }
        result, _out = self.run_script(detail)
        review_types = {row["type"] for row in result["review"]}
        self.assertIn("scale_unit", review_types)
        self.assertEqual(result["summary"]["site_geometry"], 0)


if __name__ == "__main__":
    unittest.main()
