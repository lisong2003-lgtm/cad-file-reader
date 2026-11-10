#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""园林块内铺装：新实现与 yuanlin_qty 0.4.37 冻结参考实现的线段/环面/面积等价回归。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _fixture_common as common  # noqa: E402

common.ensure_runtime()
common.prepare_paths()

import cad_landscape_geometry as new  # noqa: E402
import _yuanlin_legacy_ref as old  # noqa: E402

TOKENS = ["景观铺地", "铺装", "铺地", "园路", "波打", "收边", "PAVING", "HARDSCAPE", "PAVE"]
RULES = {"paving_layer_tokens": TOKENS, "geometry_close_tolerance": 50}


class LandscapeEquivalenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cad-land-test-")
        cls.base = Path(cls.tmp.name)
        cls.dxf = cls.base / "fixture.dxf"
        common.make_fixture(cls.dxf)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_segments_and_faces_equal_old_implementation(self):
        new_info = new._dxf_block_paving_segments(self.dxf, RULES)
        old_info = old._dxf_block_paving_segments(self.dxf, RULES)
        self.assertEqual(len(new_info["segments"]), 30)
        self.assertEqual(len(old_info["segments"]), 30)
        self.assertEqual(Counter(map(tuple, new_info["segments"])), Counter(map(tuple, old_info["segments"])))
        self.assertEqual(new_info["layers"], old_info["layers"])
        self.assertEqual(new_info.get("mm_per_unit"), old_info.get("mm_per_unit"))

        def faces_by_layer(info):
            grouped = {}
            for seg, layer in zip(info["segments"], info["layers"]):
                grouped.setdefault(layer, []).append(tuple(seg))
            return {layer: old._faces(segs, 50.0 / 1000.0) for layer, segs in grouped.items()}

        new_faces = faces_by_layer(new_info)
        old_faces = faces_by_layer(old_info)
        self.assertEqual(sorted(new_faces), sorted(old_faces))
        for layer in sorted(new_faces):
            self.assertEqual([len(f[0]) for f in new_faces[layer]], [len(f[0]) for f in old_faces[layer]])
            self.assertTrue(all(len(f[0]) == 16 for f in new_faces[layer]))
            for (new_poly, new_area), (old_poly, old_area) in zip(new_faces[layer], old_faces[layer]):
                self.assertLessEqual(abs(new_area - old_area), 1e-6)

    def test_block_refs_equal_old_implementation(self):
        self.assertEqual(new._dxf_block_ref_records(self.dxf), old._dxf_block_ref_records(self.dxf))

    def test_fallback_payload_and_cli_contract(self):
        payload = new.block_fallback_payload(self.dxf, RULES, with_paving=True, with_refs=True)
        self.assertEqual(len(payload["paving_rings"]), 2)
        self.assertEqual(len(payload["block_refs"]), 2)
        self.assertEqual(payload["summary"]["paving_rings"], 2)
        for row in payload["paving_rings"]:
            self.assertEqual(row["point_count"], 16)
            self.assertEqual(row["confidence"], 0.4)
            self.assertFalse(row["final_quantity"])
            self.assertEqual(row["review_note"], "块内推定")
            self.assertTrue(row["source_block"])
            self.assertTrue(row["layer"])
            self.assertGreater(row["area_drawing_units2"], 0)
            self.assertEqual(row["unit"], "drawing_unit^2")

        out_dir = self.base / "landscape"
        subprocess.run(
            [sys.executable, str(common.SCRIPTS / "cad_landscape_geometry.py"),
             "--block-paving", str(self.dxf), "--block-refs", str(self.dxf), "--out-dir", str(out_dir)],
            check=True, capture_output=True, text=True,
        )
        out = json.loads((out_dir / "fixture.landscape.json").read_text(encoding="utf-8"))
        self.assertEqual(len(out["paving_rings"]), 2)
        self.assertEqual(len(out["block_refs"]), 2)
        self.assertEqual(out["contract"]["summary"]["candidate_count"], 0)
        self.assertEqual(out["contract"]["summary"]["review_required"], 4)
        self.assertTrue(all(r["confidence_tier"] == "review_required" for r in out["contract"]["review_candidates"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
