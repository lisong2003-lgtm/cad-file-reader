#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""塔吊布置识图包：合成图与纯函数回归。"""
from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import cad_crane_geometry as cg  # noqa: E402
import cad_scan  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "crane_sample.dxf"


def _row(x, y, block="TOWER_CRANE", layer="塔吊", base=(0.0, 0.0), rotation=0.0,
         xscale=1.0, yscale=1.0, text=None, kind="INSERT", z=0.0):
    return cg._normalize_record({
        "kind": kind,
        "text": text if text is not None else block,
        "block_name": block if kind == "INSERT" else None,
        "layer": layer,
        "x": x,
        "y": y,
        "z": z,
        "rotation": rotation,
        "xscale": xscale,
        "yscale": yscale,
        "zscale": 1.0,
        "base_point": list(base),
        "base_point_source": "block_header" if base is not None else None,
    })


def _find(payload, block_name):
    return next(t for t in payload["crane_layout"] if t["block_name"] == block_name)


class CraneGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = cg.load_rules()
        cls.rows, cls.circles, cls.meta, cls.notes, cls.source_paths, cls.kind = cg.load_input(
            FIXTURE, 200000, lambda _s: None)
        cls.payload = cg.build_payload(
            FIXTURE, cls.rows, cls.circles, cls.meta, cls.notes, cls.source_paths, cls.kind,
            "mm", cls.rules, "2026-11-09T20:00:00+08:00", ["cad_crane_geometry"])

    def test_affine_center_zero_base_rotation_30(self):
        tower = _find(self.payload, "TC7015")
        self.assertEqual(tower["center_xy_m"], (100.0, 50.0))
        self.assertEqual(tower["center_status"], "insert_point")
        self.assertEqual(tower["transform_status"], "insert_affine")
        self.assertAlmostEqual(tower["rotation_deg"], 30.0)

    def test_affine_center_nonzero_block_base(self):
        # 块基点 (5000,5000) 的 INSERT 在 (20000,20000)：中心应为 (15000,15000) mm。
        tower = _find(self.payload, "OFFSET_CRANE")
        self.assertEqual(tower["center_xy_m"], (15.0, 15.0))
        self.assertEqual(tower["center_status"], "insert_point")

    def test_duplicate_symbols_within_2m_deduped_and_id_stable(self):
        towers = self.payload["crane_layout"]
        self.assertEqual(len(towers), 3)
        tower = _find(self.payload, "TC7015")
        self.assertEqual(len(tower["duplicates"]), 1)
        self.assertAlmostEqual(tower["duplicates"][0]["distance_m"], 0.8)
        ids = [t["crane_id"] for t in towers]
        again = cg.build_payload(
            FIXTURE, self.rows, self.circles, self.meta, self.notes, self.source_paths, self.kind,
            "mm", self.rules, "2026-11-09T20:00:01+08:00", ["cad_crane_geometry"])
        self.assertEqual(ids, [t["crane_id"] for t in again["crane_layout"]])

    def test_circle_is_annotation_only_never_jib(self):
        tower = _find(self.payload, "TC7015")
        self.assertEqual(tower["jib_length_m"], 70.0)
        self.assertEqual(tower["jib_length_source"], "text")
        legend_circles = [c for c in tower["radius_circles_m"] if c["source"] == "annotation"]
        self.assertTrue(legend_circles, "20 m 外图例圈应保留为 annotation 旁证")
        self.assertTrue(all(c["used_as_jib_length"] is False for c in tower["radius_circles_m"]))
        self.assertTrue(all(c["radius_m"] != tower["jib_length_m"] for c in tower["radius_circles_m"]))

    def test_legend_circle_20m_and_radius_text_do_not_set_jib(self):
        tower = _find(self.payload, "TOWER-CRANE")
        self.assertIsNone(tower["jib_length_m"])
        self.assertEqual(tower["jib_length_source"], "none")
        self.assertTrue(any(c["source"] == "annotation" for c in tower["radius_circles_m"]))
        self.assertFalse(any("85" in str(r.get("text")) for r in self.payload["jib_evidence"]
                             if r["crane_id"] == tower["crane_id"] and r["status"] == "candidate"))

    def test_missing_model_stays_unknown_and_weak_context_not_adopted(self):
        tower = _find(self.payload, "TOWER-CRANE")
        self.assertEqual(tower["model_status"], "unknown")
        self.assertIsNone(tower["model"])
        self.assertIsNone(tower["model_text"])

        rows = [
            _row(10000, 20000, block="TOWER_CRANE", layer="塔吊"),
            _row(15000, 20000, block=None, layer="轴线", kind="TEXT", text="TC7015"),
        ]
        towers, _ = cg.detect_towers(rows, self.rules, 0.001, "explicit")
        cg.bind_text_evidence(towers, rows, [], self.rules, 0.001)
        self.assertEqual(towers[0]["model_status"], "unknown")
        self.assertIsNone(towers[0]["model"])
        self.assertTrue(any(r["type"] == "model_text_context_weak" for r in cg.bind_text_evidence(
            cg.detect_towers(rows, self.rules, 0.001, "explicit")[0], rows, [], self.rules, 0.001)[3]))

        # 15 m 外的型号文字也不采纳
        far_rows = [
            _row(10000, 20000, block="TOWER_CRANE", layer="塔吊"),
            _row(40000, 20000, block=None, layer="塔吊文字", kind="TEXT", text="塔吊 TC7015"),
        ]
        far_towers, _ = cg.detect_towers(far_rows, self.rules, 0.001, "explicit")
        cg.bind_text_evidence(far_towers, far_rows, [], self.rules, 0.001)
        self.assertEqual(far_towers[0]["model_status"], "unknown")

    def test_dwg_worker_insert_9_and_8_fields(self):
        nine = cad_scan._insert_worker_row(
            (7, 100.0, 200.0, 0.0, 1.0, 2.0, 0.5, math.radians(30), "TC7015"), "塔吊")
        self.assertEqual(nine[1], "TC7015")
        self.assertEqual(nine[2], [100.0, 200.0, 0.0])
        self.assertAlmostEqual(nine[4], 30.0)
        self.assertEqual(nine[5], [1.0, 2.0, 0.5])
        old = cad_scan._insert_worker_row((8, 1.0, 2.0, 0.0, 1.0, 1.0, 1.0, math.radians(90)), "L")
        self.assertEqual(old[1], "")
        self.assertAlmostEqual(old[4], 90.0)

    def test_missing_drawing_unit_marks_all_towers_review(self):
        rows, circles, meta, notes, source_paths, input_kind = cg.load_input(FIXTURE, 200000, lambda _s: None)
        payload = cg.build_payload(
            FIXTURE, rows, circles, meta, notes, source_paths, input_kind,
            "mm", self.rules, "2026-11-09T20:00:02+08:00", ["cad_crane_geometry"],
            unit_explicit=False,
        )
        self.assertEqual(payload["units"]["basis"], "assumed_mm")
        self.assertEqual(payload["summary"]["review_towers"], len(payload["crane_layout"]))
        for tower in payload["crane_layout"]:
            self.assertEqual(tower["status"], "review")
            self.assertIn("missing_unit", tower["review_reasons"])

    def test_dxf_insert_before_block_header_backfills_base_point(self):
        text = """0
SECTION
2
ENTITIES
0
INSERT
8
塔吊
2
CRANE-X
10
100
20
200
30
0
0
ENDSEC
0
SECTION
2
BLOCKS
0
BLOCK
8
0
2
CRANE-X
70
0
10
10
20
20
30
0
0
ENDBLK
0
ENDSEC
0
EOF
"""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "reverse_order.dxf"
            path.write_text(text, encoding="utf-8")
            recs, _layers, _notes, _meta = cad_scan.dxf_records(
                str(path), 200000, lambda _s: None, include_insert=True)
        inserts = [r for r in recs if r["kind"] == "INSERT"]
        self.assertEqual(len(inserts), 1)
        self.assertEqual(inserts[0]["base_point"], [10.0, 20.0])
        self.assertEqual(inserts[0]["base_point_source"], "block_header_backfill")


if __name__ == "__main__":
    unittest.main()
