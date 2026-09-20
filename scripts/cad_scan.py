#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cad_scan.py — 低内存、免 CAD 软件的 DWG/DXF 图纸文字与构件型号提取器。

设计要点（与 cad-file-reader 的区别）：
  * 不构建整张图的实体对象树（那是内存/耗时大户），只按需解出文字、图层、块名。
  * DWG 走 ezdwg.raw.* 单类解码器；DXF 走逐行 tag 流式解析，两者都不渲染图片。
  * 每个解码阶段带 SIGALRM 时间预算，超时自动跳过，绝不卡死。

用法：
  python3 cad_scan.py 图纸.dwg                      # Markdown 构件清单到 stdout
  python3 cad_scan.py 目录 --glob "*.dwg" -o out     # 批量，写 out.md/out.json/out.csv
  python3 cad_scan.py 图纸.dwg --filter "板厚|C30"    # 只要含关键词的原文
"""
from __future__ import annotations

import argparse

# ---- 内存看门狗（2026-08-31）：大文件会被 read_cad.py 的 20MB 入口闸导流到这里，
#      低内存路径同样要兜底，越线立即自杀，绝不允许把整机拖到卡死 ====
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
try:
    import mem_guard as _mg
    _mg.start(int(_os.environ.get("CAD_MEM_LIMIT_MB", "4096")), name="cad_scan内存闸")
except Exception as _e:
    print("[cad_scan内存闸] 看门狗未启用: %s" % _e, file=_sys.stderr)

import csv
import math
import fnmatch
import io
import json
import os
import re
import signal
import sys
from collections import Counter, defaultdict
from pathlib import Path

VENDOR = Path.home() / ".codex/skills/cad-file-reader/vendor"
if VENDOR.is_dir():
    sys.path.insert(0, str(VENDOR))


def ensure_runtime() -> None:
    """ezdwg 的 C 扩展按特定 Python 版本编译；当前解释器不匹配时自动换到可用解释器。"""
    if os.environ.get("CAD_SCAN_REEXEC") or not str(sys.argv[0]).endswith("cad_scan.py"):
        return
    try:
        sys.path.insert(0, str(VENDOR)) if str(VENDOR) not in sys.path else None
        import ezdwg  # noqa: F401
        return
    except Exception:
        pass
    import glob
    cands = [str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3")]
    cands += sorted(glob.glob(str(Path.home() / ".cache/codex-runtimes/*/dependencies/python/bin/python3")))
    cur = os.path.realpath(sys.executable)
    for c in cands:
        if os.path.isfile(c) and os.path.realpath(c) != cur:
            os.environ["CAD_SCAN_REEXEC"] = "1"
            os.execv(c, [c] + sys.argv)


ensure_runtime()

# ---------------------------------------------------------------- 超时保护
class Budget(Exception):
    pass


class stage:
    """with stage(60): ...  超时会抛 Budget，不影响主进程。"""

    def __init__(self, seconds: float):
        self.seconds = seconds

    def __enter__(self):
        self._old = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, self._boom)
        signal.setitimer(signal.ITIMER_REAL, max(0.1, self.seconds))
        return self

    def _boom(self, *_a):
        raise Budget("time budget exceeded")

    def __exit__(self, *exc):
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, self._old or signal.SIG_DFL)
        return False


# ---------------------------------------------------------------- 构件型号规则
# 平法/结构图常见编号。顺序敏感：先长前缀，后单字母。
CODE_PATTERNS = [
    ("梁", re.compile(r"(?<![A-Za-z])(WKL|XL|LL|JZL|JGL|TXL|KL|DL|TL|WL|ZHL|QL|L)(\d{1,3}[a-f]?)\s*(\(\s*\d{1,3}\s*[AB]?\s*\))?", re.I)),
    ("板", re.compile(r"(?<![A-Za-z])(YKB|ZKB|KB|ZJB|QJB|XJB|LB|WB|XB|YB|DB|SB|CB|B|板)(\d{1,3}[a-f]?)(?![A-Za-z0-9])")),
    ("柱", re.compile(r"(?<![A-Za-z])(ZKZ|KZ|LZ|XKZ|GZ|GJZ|GGZ|ZH|TZ|JZ)(\d{1,3}[a-f]?)(?![A-Za-z0-9])")),
    ("墙", re.compile(r"(?<![A-Za-z])(YQZ|GBZ|FBZ|JLQ|LLQ|YQ|Q)(\d{1,3}[a-f]?)(?![A-Za-z0-9])")),
    ("基础", re.compile(r"(?<![A-Za-z])(JL|DJ|PJ|YJ|BJ|ZJ|JC|CT|RMB)(\d{1,3}[a-f]?)(?![A-Za-z0-9])")),
    # 门窗：前缀 + 4 位数字（前2位x100=洞口宽，后2位x100=洞口高）[推测]
    ("门窗", re.compile(r"(?<![A-Za-z0-9])(FBM|MHC|YHC|FHC|LMC|LGC|QMC|MFC|MC|FM|LC|SC|TC|PC|KC|GC|XC|ZC|DC|BC|VC|WM|CM|HM|LM|GM|DM|TM|XM|ZM|YLM|M|C)([甲乙丙]?)(\d{4})([A-Za-z]?)(?![0-9A-Za-z])")),
]
SIZE = re.compile(r"(?<!\d)(\d{2,4})\s*[x×*X]\s*(\d{2,4})(?!\d)")
CONC = re.compile(r"(?<![A-Za-z0-9])(C\d{2})(?![0-9A-Za-z])")
SLAB_THK = re.compile(r"(?:板厚|h\s*[=:]\s*|t\s*[=:]\s*)(6\d|7\d|8\d|9\d|[123]\d{2})(?:\s*mm)?", re.I)
REBAR = re.compile("[Φ\u03a6ⅠⅡⅢⅣ]{0,2}\\s*\\d{1,2}\\s*@\\s*\\d{2,3}(?:\\s*/\\s*\\d{2,3})?(?:\\s*\\(\\s*\\d{1,2}\\s*\\))?|[ⅠⅡⅢⅣΦ\u03a6]\\s*\\d{1,2}")

# 平法标注拆解
SPAN = re.compile(r"\(\s*(\d{1,3})\s*([AB])?\s*\)")
SEC_BH = re.compile(r"(?<![\d.])(\d{2,3})\s*[x×*X]\s*(\d{3,4})(?![\d.])")
STIRRUP = re.compile(r"([ⅠⅡⅢⅣΦ\u03a6])?\s*(\d{1,2})\s*@\s*(\d{2,3})(?:\s*/\s*(\d{2,3}))?(?:\s*\(\s*(\d{1,2})\s*\))?")
LONGIT_SEQ = re.compile(r"(?<![\d.A-Za-z\u2160-\u2163\u03a6])(\d{1,2}\s*[\u2160\u2161\u2162\u2163\u03a6]\s*\d{1,2}(?:\s*\+\s*\d{1,2}\s*[\u2160\u2161\u2162\u2163\u03a6]\s*\d{1,2})*)")
LONGIT_ONE = re.compile(r"(\d{1,2})\s*([\u2160\u2161\u2162\u2163\u03a6])\s*(\d{1,2})")
COVER = re.compile(r"保护层[^\d]{0,6}(\d{2,3})")
SEISMIC = re.compile(r"抗震等级?\s*[为:\uff1a=]?\s*(特[一二三]级|一级|二级|三级|四级)")
SPEC_ORDER = ("板厚", "混凝土等级", "保护层", "抗震等级")
DOOR_LAYER = re.compile(r"门窗|洞口|玻璃|m-|c-|win|door", re.I)
PRACTICE_PAT = re.compile(
    r"(屋面|楼面|地面|墙面|内墙|外墙|顶棚|天棚|散水|勒脚|踢脚|防水|保温|门窗|栏杆|涂料|饰面|防潮)"
    r"(?:做法)?\s*[:：]"
)

TEXT_KINDS = ("text", "mtext", "attrib")
_OK_CHARS = re.compile(r"[\u4e00-\u9fff\w\u3000-\u303f．，、；：（）()／/%±≤≥Φ\-+.,;:()\[\]/*=&#°~@\u2014\u2018\u2019\u201c\u201d\\s]")


def readable(s: str) -> bool:
    """过滤天正/T3 导出对象等产生的乱码串：有效字符占比过低就丢弃。"""
    s = (s or "").strip()
    if not s:
        return False
    return len(_OK_CHARS.findall(s)) / max(1, len(s)) >= 0.8


def extract_practices(t: str, file_idx, sheet, layer):
    rows = []
    for seg in re.split(r"[。；;\n]+", t or ""):
        seg = seg.strip()
        m = PRACTICE_PAT.search(seg)
        if m and len(seg) <= 400:
            txt = re.sub(r"^\s*[（(]?\d+[）).、]?\s*", "", seg)
            rows.append({"part": m.group(1), "text": txt[:200],
                         "file": file_idx, "sheet": sheet, "layer": layer})
    return rows


CAD_ESCAPES = {
    "%%130": "\u2160", "%%131": "\u2161", "%%132": "\u2162", "%%133": "\u2163", "%%134": "\u2164",
    "%%c": "\u03a6", "%%d": "\u00b0", "%%p": "\u00b1", "%%%%": "%",
}


def normalize(s: str) -> str:
    '''AutoCAD/天正 文字转义还原：%%130~%%134 = 一~四级钢符号，%%c=直径，反斜杠U+XXXX=Unicode。'''
    if not s:
        return ""
    for k, v in CAD_ESCAPES.items():
        s = s.replace(k, v).replace(k.upper(), v)
    s = re.sub(r"\\U\+([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), s)
    return s


def clean_mtext(s: str) -> str:
    s = re.sub(r"\\[A-Za-z][^;{}]*;", " ", s or "")
    s = re.sub(r"[{}]", " ", s)
    s = s.replace("\\P", " ").replace("\\~", " ")
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- DWG
DECODERS = {
    "layers": "decode_layer_names",
    "text": "decode_text_entities",
    "mtext": "decode_mtext_entities",
    "attrib": "decode_attrib_entities",
    "insert": "decode_insert_entities",
    "blocks": "decode_block_header_names",
    "line": "decode_line_entities",
    "lwpoly": "decode_lwpolyline_entities",
}
GEOM_KINDS = ("line", "lwpoly")


def _worker(name: str, path: str) -> int:
    """子进程模式：只解一类对象，逐行输出 JSON，进程退出即彻底释放内存。"""
    import ezdwg  # noqa: F401
    from ezdwg import raw

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    def safe(v):
        if isinstance(v, str):
            v = v.encode("utf-8", "replace").decode("utf-8", "replace")
            return "".join(ch if ch >= " " or ch == "\t" else " " for ch in v)
        return v

    fn = getattr(raw, DECODERS[name])
    rows = fn(path) or []
    layer_by_handle: dict[int, str] = {}
    if name not in ("layers", "blocks") and rows:
        try:
            layer_names = dict(raw.decode_layer_names(path) or [])
            handles = [r[0] for r in rows if isinstance(r[0], int)]
            if handles:
                ent_layers = raw.decode_object_entity_layer_handles(path, handles) or []
                layer_by_handle = {
                    ent_handle: layer_names.get(layer_handle, "")
                    for ent_handle, layer_handle in ent_layers
                }
        except Exception:
            pass
    for row in rows:
        layer_name = str(layer_by_handle.get(row[0], "") or "") if isinstance(row[0], int) else ""
        out = [None, None, None, layer_name]
        for item in row:
            if out[2] is None and isinstance(item, (tuple, list)) and len(item) == 3:
                out = [row[0], row[1] if isinstance(row[1], str) else None, [float(x) if isinstance(x, (int, float)) else None for x in item]]
                out.append(layer_name)
                break
        if out[1] is None and isinstance(row[1], str):
            out[1] = row[1]
            out[3] = layer_name
        if name in ("layers", "blocks"):
            out = [row[0], str(row[1] or ""), None, None]
        if name == "insert":
            out = [row[0], str(row[-1] or ""), [row[1] if isinstance(row[1], (int, float)) else None,
                                                  row[2] if isinstance(row[2], (int, float)) else None], layer_name]
        if name == "line" and len(row) >= 6:
            out = [row[0], None, [row[1], row[2], row[4], row[5]], layer_name]
        if name == "lwpoly":
            flat = []
            vs = row[2] if len(row) > 2 and isinstance(row[2], list) else []
            for pt in vs[:300]:
                if isinstance(pt, (tuple, list)) and len(pt) >= 2:
                    flat += [pt[0], pt[1]]
            out = [row[0], None, flat, layer_name]
        try:
            sys.stdout.write(json.dumps([safe(x) for x in out], ensure_ascii=True, default=float) + "\n")
        except Exception:
            continue
    sys.stdout.flush()
    return 0


def _rows(name: str, path: str, budget: float, notes: list):
    """在子进程里解一类对象，逐行收回 JSON；子进程退出即释放内存。"""
    import subprocess
    cmd = [sys.executable, os.path.abspath(__file__), "--worker", name, path]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=budget)
    except subprocess.TimeoutExpired:
        notes.append(f"{name} 解码超 {budget:.0f}s 预算，已终止（该图纸此类对象过多）")
        return None
    except Exception as e:
        notes.append(f"{name} 解码异常：{e}")
        return None
    if cp.returncode != 0:
        err = (cp.stderr or "").strip().splitlines()
        notes.append(f"{name} 解码失败：{err[-1][:120] if err else cp.returncode}")
        return None
    rows = []
    for line in cp.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue  # 个别乱码行跳过，不影响整体
    return rows


def dwg_records(path: str, want: set[str], per_stage: float, max_rows: int, log, want_blocks: bool = False) -> tuple[list[dict], list[str], list[str], dict]:
    notes: list[str] = []
    recs: list[dict] = []
    layers: list[str] = []
    meta: dict = {}
    import subprocess

    def call(name, budget):
        if name in ("mtext", "attrib"):
            budget *= 3  # 这两类是 C 层全对象扫描，大图明显更慢
        return _rows(name, path, budget, notes)

    rows = call("layers", per_stage)
    if rows:
        layers = [str(r[1]) for r in rows if r and r[1]]
    log(f"图层 {len(layers)} 个")

    for name, kind in (("text", "TEXT"), ("mtext", "MTEXT"), ("attrib", "ATTRIB")):
        if name not in want:
            continue
        rows = call(name, per_stage)
        if not rows:
            continue
        for r in rows:
            if len(recs) >= max_rows:
                notes.append(f"文字数达上限 {max_rows}，已截断")
                break
            txt = str(r[1] or "")
            if name != "text":
                txt = clean_mtext(txt)
            pt = r[2] or [None, None]
            recs.append({"kind": kind, "text": txt, "x": pt[0] if len(pt) > 0 else None,
                         "y": pt[1] if len(pt) > 1 else None,
                         "layer": r[3] if len(r) > 3 else None})
        log(f"{kind} {len([x for x in recs if x['kind'] == kind])} 条")

    if "insert" in want:
        rows = call("insert", per_stage)
        if rows:
            meta["insert_count"] = len(rows)
            meta["block_refs"] = dict(Counter(str(r[1]) for r in rows if r[1]).most_common(40))
            for r in rows:
                if len(recs) >= max_rows:
                    break
                if r[1] and not r[1].startswith("*"):
                    recs.append({"kind": "INSERT", "text": r[1], "x": (r[2] or [None, None])[0],
                                 "y": (r[2] or [None, None])[1],
                                 "layer": r[3] if len(r) > 3 else None})
        log(f"块引用 {meta.get('insert_count', 0)} 个")

    rows = call("blocks", per_stage) if want_blocks else None
    if rows:
        meta["block_defs"] = sorted({str(r[1]) for r in rows if r[1]})[:2000]
        log(f"块定义 {len(meta['block_defs'])} 个")

    return recs, layers, notes, meta


def _f(row, idx, comp):
    try:
        v = row[idx]
        if isinstance(v, (tuple, list)) and len(v) > comp:
            return float(v[comp])
    except Exception:
        pass
    return None


# ---------------------------------------------------------------- DXF（流式，不加载几何）
def dxf_records(path: str, max_rows: int, log) -> tuple[list[dict], list[str], list[str], dict]:
    recs: list[dict] = []
    layers: set[str] = set()
    blocks: Counter = Counter()
    notes: list[str] = []
    meta: dict = {}
    kind = None
    buf: dict = {}
    mtext_parts: list[str] = []

    def flush():
        nonlocal buf, mtext_parts
        if not buf:
            return
        layer = buf.get("8")
        if layer:
            layers.add(layer)
        if buf.get("_kind") in ("TEXT", "MTEXT", "ATTRIB", "ATTDEF"):
            txt = " ".join(p for p in ([buf.get("1", "")] + mtext_parts) if p)
            if txt.strip():
                recs.append({"kind": buf["_kind"], "text": clean_mtext(txt),
                             "x": _num(buf.get("10")), "y": _num(buf.get("20")),
                             "layer": layer or None})
        if buf.get("_kind") == "INSERT" and buf.get("2"):
            blocks[buf["2"]] += 1
        buf = {}
        mtext_parts = []

    with open(path, "r", errors="ignore", encoding="utf-8", newline=None) as fh:
        sec = ""
        it = iter(fh)
        for a, b in zip(it, it):
            try:
                code = a.strip()
                val = b.rstrip("\r\n")
            except Exception:
                continue
            if code == "0":
                if val == "SECTION":
                    kind = None
                    continue
                flush()
                kind = val
                if val in ("TEXT", "MTEXT", "ATTRIB", "ATTDEF", "INSERT"):
                    buf = {"_kind": val}
                else:
                    buf = {}
            elif code == "2" and kind == "SECTION":
                sec = val
            elif code == "3" and buf.get("_kind") == "MTEXT":
                mtext_parts.append(val)
            elif code == "8" and val.strip():
                layers.add(val.strip())
                buf["8"] = val.strip()
            elif buf:
                buf[code] = val
            if len(recs) >= max_rows:
                notes.append(f"文字数达上限 {max_rows}，已截断")
                break
    flush()
    meta["block_refs"] = dict(blocks.most_common(40))
    meta["insert_count"] = sum(blocks.values())
    log(f"  流式解析 DXF：文字 {len(recs)} 条 / 图层 {len(layers)} 个")
    return recs, sorted(layers), notes, meta


def detect_format(head: bytes, suffix: str) -> str:
    if head[:2] == b"AC" and len(head) >= 6 and head[2:6].isdigit():
        return "DWG"
    if head.lstrip()[:4] == b"  0" or b"SECTION" in head or suffix in (".dxf", ".dwt"):
        return "DXF"
    return "DWG"


def _num(v):
    try:
        return float(v)
    except Exception:
        return None


# ---------------------------------------------------------------- 图框/几何
LIMIT = 1e8  # 超出此量级的坐标是解码脏值，一律丢弃


def sane(*vals):
    for v in vals:
        if v is None or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > LIMIT:
            return False
    return True


FRAME_PAT = re.compile(r"图框|frame|边框|title|tlk|gb\s*a\d", re.I)


def frame_anchors(recs, min_count=2):
    """图框块的插入点通常在图框左下角，用它分图框比按空隙猜更准。"""
    seen = {}
    for r in recs:
        if r.get("kind") != "INSERT" or not r.get("text"):
            continue
        if not sane(r.get("x"), r.get("y")):
            continue
        if not FRAME_PAT.search(str(r["text"])):
            continue
        seen.setdefault((int(r["x"]), int(r["y"])), str(r["text"]))
    if len(seen) < min_count:
        return []
    return [(float(k[0]), float(k[1])) for k in seen]


def assign_sheets_by_frames(recs, anchors, min_texts=60):
    """文字归到"图框块插入点的右上侧、且在推算图幅内"的那个图框。

    图幅宽高取相邻图框块 X/Y 间距的中位数；命中率低于 45% 时返回 []，
    由调用方退回坐标空隙聚类，避免块定义区文字被远处的图框抢走。
    """
    try:
        import numpy as np
    except Exception:
        return []
    if not anchors:
        return []
    for r in recs:
        r["sheet"] = None
    xs = np.asarray([a[0] for a in anchors], float)
    ys = np.asarray([a[1] for a in anchors], float)

    def span(v):
        u = np.unique(np.round(v, 1))
        if u.size < 2:
            return 0.0
        d = np.diff(u)
        d = d[d > 1000.0]
        return float(np.median(d)) if d.size else 0.0

    w, h = span(xs), span(ys)
    if w <= 0 and h <= 0:
        return []
    w = w or h * 1.4
    h = h or w / 1.4
    idxs = [i for i, r in enumerate(recs) if sane(r.get("x"), r.get("y"))]
    if not idxs:
        return []
    PX = np.asarray([recs[i]["x"] for i in idxs], float)
    PY = np.asarray([recs[i]["y"] for i in idxs], float)
    out = np.full(len(idxs), -1, dtype=np.int64)
    CH = 2048
    for s in range(0, len(idxs), CH):
        px = PX[s:s + CH][:, None]
        py = PY[s:s + CH][:, None]
        ok = ((xs[None, :] <= px + 0.1 * w) & (ys[None, :] <= py + 0.1 * h) &
              (px - xs[None, :] <= 1.05 * w) & (py - ys[None, :] <= 1.05 * h))
        dist = np.where(ok, (px - xs[None, :]) + (py - ys[None, :]), np.inf)
        m = np.argmin(dist, axis=1)
        sel = np.nonzero(np.isfinite(dist[np.arange(m.size), m]))[0]
        out[s:s + CH][sel] = m[sel] + 1
    groups = {}
    for k, i in enumerate(idxs):
        if out[k] > 0:
            sid = int(out[k])
            recs[i]["sheet"] = sid
            groups.setdefault(sid, []).append((recs[i]["x"], recs[i]["y"]))
    hit = sum(len(v) for v in groups.values())
    if hit < 0.45 * len(idxs):
        return []
    for sid in [k for k, v in groups.items() if len(v) < min_texts]:
        groups.pop(sid, None)
        for r in recs:
            if r.get("sheet") == sid:
                r["sheet"] = None
    ordered = sorted(groups, key=lambda sid: (-max(p[1] for p in groups[sid]),
                                              min(p[0] for p in groups[sid])))
    remap = {old: new for new, old in enumerate(ordered, 1)}
    sheets = []
    for old in ordered:
        pts = groups[old]
        sheets.append({
            "id": remap[old],
            "texts": len(pts),
            "bbox": [min(p[0] for p in pts), min(p[1] for p in pts),
                     max(p[0] for p in pts), max(p[1] for p in pts)],
        })
        for r in recs:
            if r.get("sheet") == old:
                r["sheet"] = remap[old]
    return sheets


def assign_sheets(recs, bin_size=10000.0, min_texts=60):
    """按文字坐标做占据网格 + 8 邻接连通块，把一张 DWG 里的多个图框分开。

    返回 [{id, texts, bbox}]；每条记录加上 r["sheet"]（无坐标为 None）。
    """
    cells = {}
    for i, r in enumerate(recs):
        if not sane(r.get("x"), r.get("y")):
            r["sheet"] = None
            continue
        key = (int(r["x"] // bin_size), int(r["y"] // bin_size))
        cells.setdefault(key, []).append(i)
    seen = set()
    groups = []
    for key in cells:
        if key in seen:
            continue
        stack = [key]
        seen.add(key)
        comp = []
        while stack:
            cx, cy = stack.pop()
            comp.append((cx, cy))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nk = (cx + dx, cy + dy)
                    if nk in cells and nk not in seen:
                        seen.add(nk)
                        stack.append(nk)
        groups.append(comp)
    groups.sort(key=lambda g: -sum(len(cells[c]) for c in g))
    sheets = []
    for gid, comp in enumerate(groups):
        n = sum(len(cells[c]) for c in comp)
        if n < min_texts:
            for c in comp:
                for i in cells[c]:
                    recs[i]["sheet"] = None
            continue
        xs = [c[0] for c in comp]
        ys = [c[1] for c in comp]
        for c in comp:
            for i in cells[c]:
                recs[i]["sheet"] = gid
        sheets.append({"_gid": gid, "texts": n,
                       "bbox": [min(xs) * bin_size, min(ys) * bin_size,
                                (max(xs) + 1) * bin_size, (max(ys) + 1) * bin_size]})
    sheets.sort(key=lambda s: (-s["bbox"][3], s["bbox"][0]))
    old_to_new = {}
    for i, s in enumerate(sheets, 1):
        old_to_new[s["_gid"]] = i
        s["id"] = i
        s.pop("_gid", None)
    for r in recs:
        if r.get("sheet") is not None:
            r["sheet"] = old_to_new.get(r["sheet"], r["sheet"])
    return sheets


def geometry_segments(path, budget, log, include_layers=False):
    """解 LINE / LWPOLYLINE 成线段表；include_layers 时额外返回同名列表。"""
    notes = []
    segs = []
    seg_layers = [] if include_layers else None
    nline = 0
    for name in GEOM_KINDS:
        rows = _rows(name, path, budget, notes) or []
        for r in rows:
            c = r[2] if len(r) > 2 else None
            if not c:
                continue
            if name == "line":
                if len(c) >= 4 and sane(*c[:4]):
                    segs.append((c[0], c[1], c[2], c[3]))
                    if include_layers:
                        seg_layers.append(str(r[3] or "") if len(r) > 3 else "")
                    nline += 1
            else:
                pts = [(c[i], c[i + 1]) for i in range(0, len(c) - 1, 2)]
                pts = [p for p in pts if sane(*p)]
                for a, b in zip(pts, pts[1:]):
                    segs.append((a[0], a[1], b[0], b[1]))
                    if include_layers:
                        seg_layers.append(str(r[3] or "") if len(r) > 3 else "")
        log(f"{name} {len(rows)} 个对象")
    return (segs, seg_layers, notes) if include_layers else (segs, notes)


def dxf_geometry_segments(path, budget, log, include_layers=False):
    """用 ezdxf 从 DXF 模型空间取 LINE/LWPOLYLINE 线段。"""
    notes = []
    segs = []
    seg_layers = [] if include_layers else None
    try:
        import ezdxf
    except Exception as exc:
        notes.append(f"DXF 几何解码不可用：{exc}")
        return (segs, seg_layers, notes) if include_layers else (segs, notes)
    try:
        with stage(budget):
            doc = ezdxf.readfile(str(path))
            for e in doc.modelspace():
                try:
                    if e.dxftype() == "LINE":
                        s = e.dxf.start
                        t = e.dxf.end
                        if sane(float(s.x), float(s.y), float(t.x), float(t.y)):
                            segs.append((float(s.x), float(s.y), float(t.x), float(t.y)))
                            if include_layers:
                                seg_layers.append(str(e.dxf.layer or ""))
                    elif e.dxftype() == "LWPOLYLINE":
                        pts = [(float(p[0]), float(p[1])) for p in e.get_points("xy")]
                        for a, b in zip(pts, pts[1:]):
                            if sane(a[0], a[1], b[0], b[1]):
                                segs.append((a[0], a[1], b[0], b[1]))
                                if include_layers:
                                    seg_layers.append(str(e.dxf.layer or ""))
                except Exception:
                    continue
    except Exception as exc:
        notes.append(f"DXF 几何解码失败：{exc}")
    return (segs, seg_layers, notes) if include_layers else (segs, notes)


def _merge_intervals(iv):
    iv = sorted(iv)
    out = [list(iv[0])]
    for a, b in iv[1:]:
        if a - out[-1][1] <= 200:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def estimate_beam_lengths(res, seg_files, radius=3000.0):
    """[推测] 对每个带截面的梁标注点，取就近共线线段合并长度作为该处梁长。

    seg_files: 按文件分组的线段表 [[(x1,y1,x2,y2), ...], ...]，避免跨文件坐标串台。
    """
    try:
        import numpy as np
    except Exception:
        res["meta"]["geom_note"] = "环境缺少 numpy，跳过梁长估算"
        return
    pts = []
    for code, d in (res["members"].get("梁") or {}).items():
        for b in d["buckets"].values():
            if b.get("size") and sane(b.get("x"), b.get("y")):
                pts.append((code, b.get("file") or 0, b["x"], b["y"]))
    if not pts:
        return
    arrs = {}
    for fi in {p[1] for p in pts}:
        segs = seg_files[fi] if fi < len(seg_files) else []
        if not segs:
            continue
        S = np.asarray(segs, float)
        if S.ndim != 2 or S.shape[1] < 4:
            continue
        mx = (S[:, 0] + S[:, 2]) / 2.0
        my = (S[:, 1] + S[:, 3]) / 2.0
        ang = np.degrees(np.arctan2(S[:, 3] - S[:, 1], S[:, 2] - S[:, 0])) % 180.0
        ln = np.hypot(S[:, 2] - S[:, 0], S[:, 3] - S[:, 1])
        arrs[fi] = (S, mx, my, ang, ln)
    res["meta"]["geom_files"] = len(arrs)
    per = defaultdict(list)
    miss = 0
    for code, fi, x, y in pts:
        if fi not in arrs:
            miss += 1
            continue
        S, mx, my, ang, ln = arrs[fi]
        idx = np.nonzero(np.hypot(mx - x, my - y) <= radius)[0]
        idx = idx[ln[idx] > 500]
        if idx.size == 0:
            miss += 1
            continue
        base = idx[np.argmax(ln[idx])]
        a0 = ang[base]
        near = idx[np.abs(((ang[idx] - a0 + 90.0) % 180.0) - 90.0) <= 3.0]
        u = (math.cos(math.radians(a0)), math.sin(math.radians(a0)))
        iv = []
        for i in near:
            p1 = (S[i, 0] - x) * u[0] + (S[i, 1] - y) * u[1]
            p2 = (S[i, 2] - x) * u[0] + (S[i, 3] - y) * u[1]
            iv.append([min(p1, p2), max(p1, p2)])
        merged = _merge_intervals(iv)
        best = max(merged, key=lambda z: z[1] - z[0])
        per[code].append(best[1] - best[0])
    for code, lens in per.items():
        d = res["members"]["梁"][code]
        d["len_mm"] = int(round(sum(lens)))
        d["len_n"] = len(lens)
        d["len_max"] = int(round(max(lens)))
    res["meta"]["geom_radius"] = radius
    res["meta"]["geom_points"] = len(pts) - miss
    if miss:
        res["meta"]["geom_miss"] = miss


# ---------------------------------------------------------------- 分析
def cluster_records(recs, step: float):
    """把同一网格内的文字按位置合并，用于还原平法“集中标注 + 原位标注”。"""
    if step <= 0:
        return recs
    import math
    buckets = defaultdict(list)
    for r in recs:
        if not (isinstance(r.get("x"), float) and isinstance(r.get("y"), float)
                and math.isfinite(r["x"]) and math.isfinite(r["y"])):
            buckets[(10**9, 10**9)].append(r)
            continue
        buckets[(int(r["x"] // step), int(r["y"] // step))].append(r)
    out = []
    for key, group in buckets.items():
        if len(group) == 1:
            out.append(group[0])
            continue
        text = "  ".join((g["text"] or "").strip() for g in group if (g["text"] or "").strip())
        out.append({"kind": "CLUSTER", "text": text, "x": key[0] * step, "y": key[1] * step,
                    "sheet": group[0].get("sheet"), "file": group[0].get("file")})
    return out


def _spec_add(spec, spec_src, item, val, r):
    spec[item][val] += 1
    f = r.get("file")
    spec_src[item][val].add("" if f is None else str(f))


def stirrup_of(d):
    # 箍筋还原成 III6@200(2) 形式
    if not d.get("gd"):
        return ""
    s = "%s%s@%s" % (d.get("gl", ""), d["gd"], d["gp"])
    if d.get("ga"):
        s += "/" + d["ga"]
    if d.get("ge"):
        s += "(%s)" % d["ge"]
    return s


def size_key(x):
    return (x.startswith("h="), x)


def new_slot():
    return {"count": 0, "sizes": set(), "raws": [], "rebar": set(), "buckets": {}, "sheets": set(),
            "span": "", "cant": "", "w": "", "ht": "", "b": "", "h": "",
            "gl": "", "gd": "", "gp": "", "ga": "", "ge": "",
            "lt": Counter(), "note": "",
            "l_cnt": "", "l_txt": "", "l_dia": ""}


def analyse(recs, layers, meta, keep=None, dedupe=1500.0, count_by="auto"):
    """按文字规则识别构件编号。

    三种计数口径同时算出来：
      count   原文次数      —— 同一段文字出现几次（会重复计，最多）
      pos_n   标注位置数    —— 同一图框内同一位置只算一次
      sized_n 含截面/板厚数 —— 该位置的原文里带 b×h 或 h=（平法"集中标注"），最接近根数
    """
    by_cat = defaultdict(lambda: defaultdict(new_slot))
    conc = Counter()
    thk = Counter()
    spec = defaultdict(Counter)
    spec_src = defaultdict(lambda: defaultdict(set))
    keyword_rows = []
    hits = []
    practices = []
    seen_practices = set()
    for n, r in enumerate(recs):
        if r["kind"] == "INSERT":
            continue
        t = normalize((r["text"] or "")).strip()
        if not t or not readable(t):
            continue
        for p in extract_practices(t, r.get("file"), r.get("sheet"), r.get("layer")):
            key = (p["part"], p["text"])
            if key not in seen_practices:
                seen_practices.add(key)
                practices.append(p)
        x, y = r.get("x"), r.get("y")
        bk = (r.get("file"), r.get("sheet"), int(x // dedupe), int(y // dedupe)) if sane(x, y) else ("@", n)
        sized = False
        for cat, pat in CODE_PATTERNS:
            for m in pat.finditer(t):
                head_ = m.group(1).upper()
                num = m.group(3) if cat == "门窗" else (m.group(2) or "").upper()
                span_val = cant_val = wd = hg = ""
                if cat == "门窗":
                    try:
                        wi, hi = int(num[:2]) * 100, int(num[2:]) * 100
                    except ValueError:
                        wi = hi = 0
                    if not (600 <= hi <= 3900 and 300 <= wi <= 12000):
                        continue  # 尺寸不像洞口，按误命中丢弃
                    code = head_ + (m.group(2) or "") + num + (m.group(4) or "").upper()
                    wd, hg = str(wi), str(hi)
                    span_ = ""
                else:
                    code = ("板" + num) if head_ == "板" else (head_ + num)
                    try:
                        span_ = (m.group(3) or "").replace(" ", "")
                    except IndexError:
                        span_ = ""
                    if cat == "梁" and span_.startswith("("):
                        spm = SPAN.search(span_)
                        if spm:
                            span_val = spm.group(1)
                            cant_val = {"A": "一端悬挑", "B": "两端悬挑"}.get(spm.group(2) or "", "")
                if span_:
                    code += span_
                slot = by_cat[cat][code]
                slot["count"] += 1
                if span_val and not slot["span"]:
                    slot["span"], slot["cant"] = span_val, cant_val
                if wd:
                    if not slot["w"]:
                        slot["w"], slot["ht"] = wd, hg
                    slot["sizes"].add(wd + "x" + hg)
                if cat == "门窗" and head_ in ("M", "C") and not slot["note"]:
                    slot["note"] = "单字母前缀，需人工核对"
                b = slot["buckets"].get(bk)
                if b is None:
                    b = {"size": False, "x": x, "y": y, "file": r.get("file") or 0}
                    slot["buckets"][bk] = b
                if r.get("sheet"):
                    slot["sheets"].add(r["sheet"])
                sz = SIZE.search(t)
                if sz:
                    slot["sizes"].add(f"{sz.group(1)}x{sz.group(2)}")
                    b["size"] = True
                    sized = True
                sb = SEC_BH.search(t)
                if sb and not slot["b"]:
                    slot["b"], slot["h"] = sb.group(1), sb.group(2)
                sti = STIRRUP.search(t)
                if sti and not slot["gd"]:
                    slot["gl"], slot["gd"], slot["gp"] = sti.group(1) or "", sti.group(2), sti.group(3)
                    slot["ga"], slot["ge"] = sti.group(4) or "", sti.group(5) or ""
                lq = LONGIT_SEQ.search(t)
                if lq:
                    txt = re.sub(r"\s+", "", lq.group(1))
                    if sum(int(a) for a, _s, _d in LONGIT_ONE.findall(txt)):
                        slot["lt"][txt] += 1
                th = SLAB_THK.search(t)
                if th:
                    slot["sizes"].add("h=" + th.group(1))
                    b["size"] = True
                    sized = True
                for rb in REBAR.finditer(t):
                    slot["rebar"].add(re.sub(r"\s+", "", rb.group(0)))
                if len(slot["raws"]) < 3:
                    slot["raws"].append(t[:120])
                hits.append({"cat": cat, "code": code, "raw": t[:160], "x": x, "y": y,
                             "sheet": r.get("sheet"), "file": r.get("file"),
                             "kind": r["kind"]})
        for c in CONC.findall(t):
            conc[c.upper()] += 1
            _spec_add(spec, spec_src, "混凝土等级", c.upper(), r)
        th_ = SLAB_THK.search(t)
        if th_:
            thk[th_.group(1)] += 1
            _spec_add(spec, spec_src, "板厚", th_.group(1) + "mm", r)
        cv = COVER.search(t)
        if cv:
            _spec_add(spec, spec_src, "保护层", cv.group(1) + "mm", r)
        sv = SEISMIC.search(t)
        if sv:
            _spec_add(spec, spec_src, "抗震等级", sv.group(1), r)
        if keep and keep.search(t):
            keyword_rows.append({"kind": r["kind"], "text": t, "x": r["x"], "y": r["y"],
                                 "file": r.get("file"), "sheet": r.get("sheet"),
                                 "layer": r.get("layer")})
        _ = sized

    def est_of(d):
        pos_n = len(d["buckets"])
        sized_n = sum(1 for b in d["buckets"].values() if b.get("size"))
        if count_by == "raw":
            est, basis = d["count"], "原文次数"
        elif count_by == "pos":
            est, basis = pos_n, "标注位置"
        elif count_by == "label":
            est, basis = (sized_n, "集中标注") if sized_n else (pos_n, "标注位置")
        else:
            est, basis = (sized_n, "集中标注") if sized_n else (pos_n, "标注位置")
        return pos_n, sized_n, est, basis

    # 同编号梁：标了跨数的行把跨数/悬挑回填给只写编号的行
    annotated = defaultdict(list)
    for code, d in (by_cat.get("梁") or {}).items():
        sm = SPAN.search(code)
        if sm:
            annotated[code[:sm.start()]].append(d)
    for code, d in (by_cat.get("梁") or {}).items():
        if not d["span"]:
            for sib in annotated.get(code, []):
                if sib["span"]:
                    d["span"], d["cant"] = sib["span"], sib["cant"]
                    d["span_note"] = "同编号并入"
                    break
    members = {}
    for cat, v in by_cat.items():
        for code, d in v.items():
            pos_n, sized_n, est, basis = est_of(d)
            d["pos_n"], d["sized_n"], d["est"], d["basis"] = pos_n, sized_n, est, basis
            d["sheet_n"] = len(d["sheets"])
            if d["lt"]:
                d["l_txt"] = d["lt"].most_common(1)[0][0]
                ones = LONGIT_ONE.findall(d["l_txt"])
                d["l_cnt"] = sum(int(a) for a, _s, _d in ones)
                d["l_dia"] = "/".join(sorted(set(g for _a, _s, g in ones), key=int))
        members[cat] = dict(sorted(v.items(), key=lambda kv: (-kv[1]["est"], -kv[1]["count"], kv[0])))

    rebar_agg: dict[str, dict[str, list]] = {"箍筋": {}, "纵筋": {}}
    for cat in ("梁", "柱"):
        for code, d in members.get(cat, {}).items():
            s = stirrup_of(d)
            if s:
                a = rebar_agg["箍筋"].setdefault(s, [0, 0, set()])
                a[0] += 1
                a[1] += d["est"]
                a[2].add(code)
            ltxt = d.get("l_txt", "")
            if ltxt:
                a = rebar_agg["纵筋"].setdefault(ltxt, [0, 0, set()])
                a[0] += 1
                a[1] += d["est"]
                a[2].add(code)
    rebar_summary = {
        k: [
            {"型号": model, "构件型数": n, "估算根数": est,
             "构件编号": "、".join(sorted(codes)[:8])}
            for model, (n, est, codes) in sorted(v.items(), key=lambda kv: (-kv[1][1], kv[0]))
        ]
        for k, v in rebar_agg.items()
    }

    return {
        "spec": {k: dict(v.most_common()) for k, v in spec.items()},
        "spec_src": {k: {val: sorted(s) for val, s in v.items()} for k, v in spec_src.items()},
        "door_layer": [x for x in layers if DOOR_LAYER.search(x)][:10],
        "members": members,
        "concrete": dict(conc.most_common()),
        "slab_thk": dict(thk.most_common()),
        "rebar_summary": rebar_summary,
        "practices": practices[:500],
        "layers": layers,
        "meta": meta,
        "text_total": len(recs),
        "keyword_rows": keyword_rows,
        "hits": hits,
    }


# ---------------------------------------------------------------- 输出
MD_COLS = {
    "梁": ["编号", "标注跨数", "悬挑", "截面b×h", "箍筋", "纵筋", "纵筋根数", "纵筋直径",
           "根数估计", "依据", "标注位置数", "含截面数", "原文次数", "图框数",
           "梁线候选合计(m)", "单根均长(m)", "原文示例"],
    "柱": ["编号", "截面b×h", "箍筋", "纵筋", "纵筋根数", "纵筋直径",
           "根数估计", "依据", "标注位置数", "含截面数", "原文次数", "图框数", "原文示例"],
    "门窗": ["编号", "洞口宽×高(mm)", "数量估计", "依据", "标注位置数", "原文次数", "图框数", "备注", "原文示例"],
    "_": ["编号", "根数估计", "依据", "标注位置数", "含截面数", "原文次数", "图框数",
          "截面/尺寸", "配筋片段", "原文示例"],
}
CAT_UNIT = {"梁": "根", "板": "块", "柱": "根", "墙": "片", "基础": "个", "门窗": "个"}


def bh_of(d):
    return "%sx%s" % (d["b"], d["h"]) if d.get("b") and d.get("h") else ""


def md_cells(cat, code, d):
    raw = (d["raws"][0] if d["raws"] else "").replace("|", "/")[:60]
    if cat == "梁":
        ln = round(d["len_mm"] / 1000.0, 1) if d.get("len_mm") else ""
        avg = round(d["len_mm"] / 1000.0 / d["len_n"], 1) if d.get("len_mm") and d.get("len_n") else ""
        sp = d.get("span", "")
        if d.get("span_note"):
            sp = sp + chr(0x203b) if sp else ""
        return [code, sp, d.get("cant", ""), bh_of(d), stirrup_of(d), d.get("l_txt", ""),
                d.get("l_cnt", ""), d.get("l_dia", ""), d["est"], d["basis"], d["pos_n"],
                d["sized_n"], d["count"], d.get("sheet_n") or "", ln, avg, raw]
    if cat == "柱":
        return [code, bh_of(d), stirrup_of(d), d.get("l_txt", ""),
                d.get("l_cnt", ""), d.get("l_dia", ""), d["est"], d["basis"], d["pos_n"],
                d["sized_n"], d["count"], d.get("sheet_n") or "", raw]
    if cat == "门窗":
        return [code, "%sx%s" % (d["w"], d["ht"]) if d.get("w") else "", d["est"], d["basis"],
                d["pos_n"], d["count"], d.get("sheet_n") or "", d.get("note", ""), raw]
    return [code, d["est"], d["basis"], d["pos_n"], d["sized_n"], d["count"],
            d.get("sheet_n") or "", "、".join(sorted(d["sizes"], key=size_key)),
            "、".join(sorted(d["rebar"])[:3]), raw]


def spec_rows(res, files):
    name_of = dict((i, f["name"]) for i, f in enumerate(files))
    sp = res.get("spec") or {}
    order = [x for x in SPEC_ORDER if x in sp] + [x for x in sp if x not in SPEC_ORDER]
    rows = []
    for k in order:
        for val, cnt in list(sp[k].items()):
            src = (res.get("spec_src") or {}).get(k, {}).get(val, [])
            names = [name_of.get(int(i), "") for i in src[:3] if i != ""]
            rows.append([k, val, cnt, len([x for x in src if x != ""]), "；".join(n for n in names if n)])
    return rows


SPEC_CSV_HEAD = ["项目", "数值", "出现次数", "出处文件数", "出处文件"]


def to_md(res, files):
    o = io.StringIO()
    o.write("# CAD 图纸解析结果\n\n")
    o.write("| 文件 | 格式 | 文字数 | 图层数 | 耗时 | 峰值内存 |\n|---|---|---|---|---|---|\n")
    for f in files:
        o.write(f"| {f['name']} | {f['fmt']} | {f['texts']} | {f['layers']} | {f['secs']}s | {f['rss']}MB |\n")
    sheets = res["meta"].get("sheets") or []
    if len(sheets) > 1:
        o.write(f"\n**自动分图框**：识别出 {len(sheets)} 个图框（同一编号在同一图框内只计一次）\n\n")
        o.write("| 图框 | 文字数 | 坐标范围 X / Y |\n|---|---|---|\n")
        for s in sheets[:40]:
            b = s["bbox"]
            o.write(f"| {s['id']} | {s['texts']} | {int(b[0])}~{int(b[2])} / {int(b[1])}~{int(b[3])} |\n")
    if res["meta"].get("geom_note"):
        o.write("\n[提示] " + res["meta"]["geom_note"] + "\n")
    if res["concrete"]:
        o.write("\n**混凝土等级**：" + "、".join(f"{k}×{v}" for k, v in res["concrete"].items()) + "\n")
    if res["slab_thk"]:
        o.write("\n**板厚候选**：" + "、".join(f"{k}mm×{v}" for k, v in res["slab_thk"].items()) + "\n")
    for cat in ("梁", "板", "柱", "墙", "基础", "门窗"):
        items = res["members"].get(cat)
        if not items:
            continue
        total = sum(d["est"] for d in items.values())
        cols = MD_COLS.get(cat, MD_COLS["_"])
        if cat == "门窗":
            dl = res.get("door_layer") or []
            o.write("\n" + ("[提示] 本图门窗图层：" + "、".join(dl) if dl else
                                 "[提示] 本图未找到门窗图层，门窗编号可能混入预埋件等标注，务必人工核对"))
        if cat == "梁" and any(d.get("span_note") for d in items.values()):
            o.write("\n[提示] 跨数后的 ※ 表示该编号另有标了跨数的图面位置，跨数按同编号借用。\n")
        unit = CAT_UNIT.get(cat, "处")
        o.write(f"\n## {cat}（{len(items)} 种编号 / 合计约 {total} {unit}）\n\n")
        o.write("| " + " | ".join(cols) + " |\n")
        o.write("|" + "---|" * len(cols) + "\n")
        for code, d in list(items.items()):
            cells = [str(c) if c != "" else "-" for c in md_cells(cat, code, d)]
            o.write("| " + " | ".join(cells) + " |\n")
    if res.get("rebar_summary") and any(res["rebar_summary"].values()):
        o.write("\n## 钢筋型号汇总 [图面识别]\n\n")
        for kind, rows in (("箍筋", res["rebar_summary"].get("箍筋") or []),
                           ("纵筋", res["rebar_summary"].get("纵筋") or [])):
            if not rows:
                continue
            o.write(f"**{kind}**\n\n")
            o.write("| 型号 | 构件型数 | 估算根数 | 构件编号 |\n|---|---|---|---|\n")
            for row in rows:
                o.write(f"| {row['型号']} | {row['构件型数']} | {row['估算根数']} | {row['构件编号']} |\n")
            o.write("\n")
    if res.get("practices"):
        name_of = {i: f["name"] for i, f in enumerate(files)}
        o.write("\n## 建筑做法 [图面识别]\n\n")
        o.write("| 部位 | 做法原文 | 文件 | 图框 | 图层 |\n|---|---|---|---|---|\n")
        for row in res["practices"][:200]:
            o.write(f"| {row['part']} | {row['text']} | "
                    f"{name_of.get(row.get('file'), '-')} | {row.get('sheet') or '-'} | "
                    f"{row.get('layer') or '-'} |\n")
    if res.get("spec_table") and res.get("spec"):
        o.write("\n## 规格表（图面与设计说明数值汇总）\n\n")
        o.write("| 项目 | 数值 | 出现次数 | 出处文件数 | 出处文件（最多 3 个） |\n|---|---|---|---|---|\n")
        for row in spec_rows(res, files):
            o.write("| " + " | ".join(str(c) if c != "" else "-" for c in row) + " |\n")
    if res["keyword_rows"]:
        name_of = {i: f["name"] for i, f in enumerate(files)}
        seen = set()
        rows = []
        for r in res["keyword_rows"]:
            key = (r["text"], r.get("file"), r.get("sheet"),
                   round(r["x"], 1) if isinstance(r.get("x"), (int, float)) else None,
                   round(r["y"], 1) if isinstance(r.get("y"), (int, float)) else None)
            if key in seen:
                continue
            seen.add(key)
            rows.append(r)
        o.write(f"\n## 关键词命中原文（{len(res['keyword_rows'])} 条 / 去重 {len(rows)} 条）\n\n")
        o.write("| 原文 | 文件 | 图框 | 图层 | 坐标 |\n|---|---|---|---|---|\n")
        for r in rows[:400]:
            xy = (f"{r['x']:.0f},{r['y']:.0f}" if isinstance(r.get("x"), (int, float))
                  and isinstance(r.get("y"), (int, float)) else "-")
            o.write(f"| {r['text'][:160]} | {name_of.get(r.get('file'), '-')} | "
                    f"{r.get('sheet') or '-'} | {r.get('layer') or '-'} | {xy} |\n")
    if res["meta"].get("block_refs"):
        o.write("\n## 块/图例使用频次（前 20）\n\n")
        for k, v in list(res["meta"]["block_refs"].items())[:20]:
            o.write(f"- {k}：{v}\n")
    if res["layers"]:
        o.write(f"\n<details><summary>图层清单（{len(res['layers'])}）</summary>\n\n")
        o.write("、".join(res["layers"][:600]) + "\n\n</details>\n")
    o.write("\n> 根数估计口径：集中标注 > 标注位置 > 原文次数，三者同时给出便于核对；"
            "梁线候选长度为就近共线线段合并结果 [推测]，只作图面证据，不替代专业算量。\n")
    return o.getvalue()


CSV_HEAD = ["类别", "编号", "根数估计", "依据", "标注位置数", "含截面数", "原文次数", "图框数",
            "标注跨数", "悬挑", "洞口宽mm", "洞口高mm", "截面b", "截面h", "箍筋", "箍筋非加密间距",
            "箍筋肢数", "纵筋根数", "纵筋直径", "纵筋原文",
            "截面尺寸", "配筋片段", "梁线候选合计mm", "单根均长mm", "备注", "原文示例"]
REBAR_CSV_HEAD = ["类别", "型号", "构件型数", "估算根数", "构件编号"]
PRACTICE_CSV_HEAD = ["部位", "做法原文", "文件", "图框", "图层"]


def csv_rows(res):
    rows = []
    for cat, items in res["members"].items():
        for code, d in items.items():
            rows.append([cat, code, d["est"], d["basis"], d["pos_n"], d["sized_n"], d["count"],
                         d.get("sheet_n") or "", 
                         ("%s" + chr(0x203b)) % d["span"] if d.get("span_note") else d.get("span", ""),
                         d.get("cant", ""),
                         d.get("w", ""), d.get("ht", ""), d.get("b", ""), d.get("h", ""),
                         stirrup_of(d), d.get("ga", ""), d.get("ge", ""),
                         d.get("l_cnt", ""), d.get("l_dia", ""), d.get("l_txt", ""),
                         "、".join(sorted(d["sizes"], key=size_key)),
                         "、".join(sorted(d["rebar"])[:4]), d.get("len_mm") or "",
                         round(d["len_mm"] / d["len_n"]) if d.get("len_mm") and d.get("len_n") else "",
                         d.get("note", ""), (d["raws"][0] if d["raws"] else "")])
    return rows


def jsonable(res):
    keep = ("est", "basis", "pos_n", "sized_n", "count", "sheet_n", "len_mm", "len_avg_mm",
            "sizes", "rebar", "raws", "span", "cant", "span_note", "w", "ht", "b", "h",
            "gl", "gd", "gp", "ga", "ge", "l_cnt", "l_dia", "l_txt", "note")
    m = {}
    for c, v in res["members"].items():
        m[c] = {}
        for k, d in v.items():
            e = {kk: d[kk] for kk in keep if kk in d}
            e["sizes"] = sorted(d["sizes"], key=size_key)
            e["rebar"] = sorted(d["rebar"])
            e["raws"] = d["raws"]
            m[c][k] = e
    return {"members": m, "spec": res.get("spec"), "spec_src": res.get("spec_src"),
            "rebar_summary": res.get("rebar_summary"),
            "practices": res.get("practices"),
            "concrete": res["concrete"], "slab_thk": res["slab_thk"],
            "layers": res["layers"], "meta": res["meta"], "text_total": res["text_total"],
            "keyword_rows": res["keyword_rows"][:2000], "notes": res["notes"], "files": res["files"]}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="低内存 CAD 文字/构件提取（DWG/DXF，免装 CAD 软件）")
    ap.add_argument("--worker", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--worker-path", default=None, help=argparse.SUPPRESS)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--glob", default="*.dwg", help="配合目录使用，默认 *.dwg")
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument("--with-mtext", action="store_true", help="解 MTEXT（大图很慢，默认关）")
    ap.add_argument("--with-attrib", action="store_true", help="解 ATTRIB（极慢，默认关）")
    ap.add_argument("--with-insert", action="store_true", help="解块引用统计")
    ap.add_argument("--with-blocks", action="store_true", help="解块定义清单（大图较慢）")
    ap.add_argument("--detail-json", default=None,
                    help="额外写出 text_records/hits/geometry 的 detail JSON，供规范目录与规则解读使用")
    ap.add_argument("--only", default=None, help="只要这些类别，逗号分隔：梁,板,柱,墙,基础,门窗")
    ap.add_argument("--filter", dest="flt", default=None, help="只输出命中该正则的原文，如 '板厚|C30'")
    ap.add_argument("--search", dest="flt", default=None,
                    help="同 --filter：按关键词/正则查找图纸内容，输出文件、图框、图层、坐标")
    ap.add_argument("--budget", type=float, default=45.0, help="单阶段时间预算/秒，默认 45")
    ap.add_argument("--max-rows", type=int, default=200000)
    ap.add_argument("--count-by", default="auto", choices=["auto", "label", "pos", "raw"],
                    help="根数口径：auto/label=集中标注(最接近根数)，pos=标注位置去重，raw=原文次数")
    ap.add_argument("--dedupe", type=float, default=1500.0, help="标注位置去重半径/图纸单位，默认 1500")
    ap.add_argument("--no-sheet", action="store_true", help="不自动分图框（跨图框重复计）")
    ap.add_argument("--sheet-min", type=int, default=60, help="图框至少容纳多少条文字才参与去重，默认 60")
    ap.add_argument("--sheets", default="auto", choices=["auto", "frame", "grid"],
                    help="分图框方式：auto=有图框块就用块(需 --with-insert)，否则按坐标空隙；frame/grid 强制")
    ap.add_argument("--sheet-bin", type=float, default=10000.0, help="分图框网格尺寸/图纸单位，默认 10000")
    ap.add_argument("--with-geom", action="store_true", help="提取 LINE/LWPOLYLINE 几何候选，用于识图定位和复核")
    ap.add_argument("--with-geom-layer", action="store_true",
                    help="额外保存每段几何所在的图层（DWG 需解码实体句柄，供识图定位）")
    ap.add_argument("--geom-radius", type=float, default=3000.0, help="几何候选关联取标注点附近多大范围，默认 3000")
    ap.add_argument("--cluster", type=float, default=0.0, help="按此网格尺寸(图纸单位,如 1500)合并邻近文字，还原平法集中标注")
    ap.add_argument("-o", "--out", default=None, help="输出前缀，写 .md/.json/.csv")
    ap.add_argument("--format", default="md", help="md|json|csv|all")
    ap.add_argument("--spec-table", action="store_true",
                    help="额外出规格表：板厚/混凝土等级/保护层/抗震等级（md 追加一节，csv 另写 -spec.csv）")
    args = ap.parse_args()

    if args.worker:
        sys.exit(_worker(args.worker, args.paths[0]))

    want = set(TEXT_KINDS[:1])
    if args.with_mtext:
        want.add("mtext")
    if args.with_attrib:
        want.add("attrib")

    files: list[Path] = []
    for p in args.paths:
        pp = Path(p).expanduser()
        if pp.is_dir():
            it = pp.rglob("*") if args.recursive else pp.glob("*")
            files += sorted(x for x in it if x.is_file() and fnmatch.fnmatch(x.name.lower(), args.glob.lower()))
        elif pp.is_file():
            files.append(pp)
    if not files:
        print("没有找到文件", file=sys.stderr)
        return 2

    import resource
    def rss_mb():
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6)

    keep = re.compile(args.flt, re.I) if args.flt else None
    all_recs: list[dict] = []
    all_layers: set[str] = set()
    all_meta: dict = {"block_refs": {}}
    fstats: list[dict] = []
    notes: list[str] = []
    seg_files: list[list] = []
    seg_layers_files: list[list] = []

    for f in files:
        import time
        t0 = time.time()
        log = lambda s: print(f"{f.name}: {s}", file=sys.stderr)
        log("开始")
        try:
            head = f.read_bytes()[:128]
        except Exception as e:
            notes.append(f"{f.name}: 读取失败 {e}")
            continue
        fmt = detect_format(head, f.suffix.lower())
        if fmt == "DXF":
            try:
                recs, layers, n, meta = dxf_records(str(f), args.max_rows, log)
            except Exception as e:
                n, recs, layers, meta = [f"DXF 解析失败：{e}"], [], [], {}
        else:
            try:
                recs, layers, n, meta = dwg_records(
                    str(f), want | ({"insert"} if args.with_insert else set()),
                    args.budget, args.max_rows, log, want_blocks=args.with_blocks)
            except Exception as e:
                n, recs, layers, meta = [f"DWG 解析失败：{e}（如需可转 DXF）"], [], [], {}
        notes += [f"{f.name}: {x}" for x in n]
        for r in recs:
            r["file"] = len(fstats)
        if recs and not args.no_sheet:
            anchors = []
            if args.sheets in ("auto", "frame"):
                anchors = frame_anchors(recs)
            try:
                sheets = []
                if anchors and args.sheets != "grid":
                    sheets = assign_sheets_by_frames(recs, anchors, args.sheet_min)
                    if sheets:
                        notes.append(f"{f.name}: 按图框块定位（{len(sheets)}/{len(anchors)} 个图框有内容）")
                if not sheets:
                    sheets = assign_sheets(recs, args.sheet_bin)
                    if anchors and args.sheets != "grid":
                        notes.append(f"{f.name}: 图框块命中率低，改用坐标空隙分图框")
                    elif args.sheets == "frame":
                        notes.append(f"{f.name}: 没找到图框块，改用坐标空隙分图框（--with-insert 可提高准确率）")
            except Exception as e:
                sheets = []
                notes.append(f"{f.name}: 分图框失败 {e}")
            base = len(all_meta.get("sheets") or [])
            for s in sheets:
                s["id"] = s["id"] + base
                s["file"] = f.name
                all_meta.setdefault("sheets", []).append(s)
            for r in recs:
                if r.get("sheet"):
                    r["sheet"] += base
        if args.with_geom:
            if fmt == "DWG":
                if args.with_geom_layer:
                    gsegs, glayers, gn = geometry_segments(str(f), args.budget, log, include_layers=True)
                    seg_layers_files.append(glayers)
                else:
                    gsegs, gn = geometry_segments(str(f), args.budget, log)
            elif fmt == "DXF":
                if args.with_geom_layer:
                    gsegs, glayers, gn = dxf_geometry_segments(str(f), args.budget, log, include_layers=True)
                    seg_layers_files.append(glayers)
                else:
                    gsegs, gn = dxf_geometry_segments(str(f), args.budget, log)
            else:
                gsegs, gn = [], []
            notes += [f"{f.name}: {x}" for x in gn]
            seg_files.append(gsegs)
        all_recs += recs
        all_layers |= set(layers)
        for k, v in (meta.get("block_refs") or {}).items():
            all_meta["block_refs"][k] = all_meta["block_refs"].get(k, 0) + v
        all_meta["insert_count"] = all_meta.get("insert_count", 0) + (meta.get("insert_count") or 0)
        st = {"name": f.name, "path": str(f), "fmt": fmt,
              "texts": len(recs), "layers": len(layers), "secs": round(time.time() - t0, 1), "rss": rss_mb()}
        fstats.append(st)
        if args.with_geom and seg_files:
            st["segs"] = len(seg_files[-1])
        log(f"完成 {round(time.time()-t0,1)}s / 峰值内存 {rss_mb()}MB")

    res = analyse(cluster_records(all_recs, args.cluster), sorted(all_layers), all_meta, keep,
                  dedupe=args.dedupe, count_by=args.count_by)
    res["spec_table"] = bool(args.spec_table)
    if args.with_geom and any(seg_files):
        try:
            estimate_beam_lengths(res, seg_files, args.geom_radius)
        except Exception as e:
            notes.append(f"梁长估算失败：{type(e).__name__}: {e}")
    if args.only:
        pick = {x.strip() for x in args.only.split(",") if x.strip()}
        res["members"] = {c: v for c, v in res["members"].items() if c in pick}
    res["notes"] = notes
    res["files"] = fstats
    all_meta.pop("segs", None)

    md = to_md(res, fstats)
    if args.out:
        base = Path(args.out)
        base.parent.mkdir(parents=True, exist_ok=True)
        written = []
        if args.format in ("md", "all"):
            base.with_suffix(".md").write_text(md, encoding="utf-8")
            written.append(str(base.with_suffix(".md")))
        if args.format in ("json", "all"):
            base.with_suffix(".json").write_text(json.dumps(jsonable(res), ensure_ascii=False, indent=1), encoding="utf-8")
            written.append(str(base.with_suffix(".json")))
        if args.format in ("csv", "all"):
            with base.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as fh:
                w = csv.writer(fh)
                w.writerow(CSV_HEAD)
                w.writerows(csv_rows(res))
            if args.spec_table and res.get("spec"):
                with base.with_name(base.name + "-spec.csv").open("w", newline="", encoding="utf-8-sig") as fh:
                    w = csv.writer(fh)
                    w.writerow(SPEC_CSV_HEAD)
                    w.writerows(spec_rows(res, fstats))
            if res.get("rebar_summary") and any(res["rebar_summary"].values()):
                with base.with_name(base.name + "-rebar.csv").open("w", newline="", encoding="utf-8-sig") as fh:
                    w = csv.writer(fh)
                    w.writerow(REBAR_CSV_HEAD)
                    for kind in ("箍筋", "纵筋"):
                        for row in res["rebar_summary"].get(kind) or []:
                            w.writerow([kind, row["型号"], row["构件型数"], row["估算根数"], row["构件编号"]])
            if res.get("practices"):
                with base.with_name(base.name + "-practices.csv").open("w", newline="", encoding="utf-8-sig") as fh:
                    w = csv.writer(fh)
                    w.writerow(PRACTICE_CSV_HEAD)
                    name_of = {i: f["name"] for i, f in enumerate(fstats)}
                    for row in res["practices"]:
                        w.writerow([row["part"], row["text"], name_of.get(row.get("file"), ""),
                                    row.get("sheet") or "", row.get("layer") or ""])
            written.append(str(base.with_suffix(".csv")))
        print("已写出 " + "、".join(written), file=sys.stderr)
    else:
        if args.format == "json":
            print(json.dumps(jsonable(res), ensure_ascii=False, indent=1))
        elif args.format == "csv":
            w = csv.writer(sys.stdout)
            w.writerow(CSV_HEAD)
            w.writerows(csv_rows(res))
            if args.spec_table and res.get("spec"):
                print("", end="")
                w.writerow([])
                w.writerow(SPEC_CSV_HEAD)
                w.writerows(spec_rows(res, fstats))
        else:
            print(md)
    if notes:
        print("\n[提示] " + "；".join(notes), file=sys.stderr)
    if args.detail_json:
        detail = jsonable(res)
        detail["text_records"] = all_recs
        detail["hits"] = res.get("hits") or []
        detail["geometry_segments"] = seg_files if args.with_geom else []
        detail["geometry_layers"] = seg_layers_files if args.with_geom_layer else []
        detail_path = Path(args.detail_json)
        detail_path.parent.mkdir(parents=True, exist_ok=True)
        detail_path.write_text(
            json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"已写出详情 {detail_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
