#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试共用：固定解释器、vendor 路径与合成 DXF。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PYTHON = Path(os.environ.get("CODEX_RUNTIME_PYTHON") or (Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"))
SCRIPTS = ROOT / "scripts"
VENDOR = ROOT / "vendor"
YUANLIN_SCRIPTS = Path.home() / ".codex" / "skills" / "yuanlin-suanliang" / "scripts"


def ensure_runtime() -> None:
    """系统 python 缺兼容 numpy 时，切到本机 runtime python 再跑测试。"""
    if sys.executable == str(RUNTIME_PYTHON) or not RUNTIME_PYTHON.exists():
        return
    for p in (str(VENDOR), str(SCRIPTS)):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        import ezdxf  # noqa: F401
    except Exception:
        target = Path(sys.argv[0]) if sys.argv else Path()
        if target.exists() and target.name != "__main__.py":
            argv = [str(RUNTIME_PYTHON), str(target), *sys.argv[1:]]
        else:
            argv = [str(RUNTIME_PYTHON), "-m", "unittest", *sys.argv[1:]]
        os.execv(str(RUNTIME_PYTHON), argv)


def prepare_paths() -> None:
    for p in (str(VENDOR), str(SCRIPTS), str(YUANLIN_SCRIPTS)):
        if p not in sys.path:
            sys.path.insert(0, p)


def make_fixture(path: Path) -> None:
    import ezdxf

    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    a = doc.blocks.new(name="BLK-A", base_point=(100.0, 50.0))
    a.add_line((100.0, 50.0), (300.0, 50.0), dxfattribs={"layer": "S-BEAM"})
    a.add_lwpolyline(
        [(100.0, 50.0, 0.0), (300.0, 50.0, 0.5), (300.0, 250.0, 0.0), (100.0, 250.0, 0.0)],
        format="xyb", close=True, dxfattribs={"layer": "景观铺装"},
    )
    b = doc.blocks.new(name="BLK-B", base_point=(0.0, 0.0))
    b.add_line((0.0, 0.0), (0.0, 100.0), dxfattribs={"layer": "S-COLUMN"})
    b.add_blockref("BLK-A", (500.0, 0.0), dxfattribs={"layer": "0", "xscale": 1.0, "yscale": 1.0, "rotation": 90.0})
    msp.add_line((0.0, 0.0), (100.0, 0.0), dxfattribs={"layer": "S-SLAB"})
    msp.add_blockref("BLK-A", (1000.0, 0.0), dxfattribs={"layer": "S-BEAM-梁", "xscale": 2.0, "yscale": 1.5, "rotation": 30.0})
    msp.add_blockref("BLK-B", (0.0, 500.0), dxfattribs={"layer": "S-WALL", "xscale": 1.0, "yscale": 1.0, "rotation": 0.0})
    doc.saveas(path)
