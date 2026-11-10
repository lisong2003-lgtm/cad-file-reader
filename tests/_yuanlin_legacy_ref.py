#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试专用：yuanlin-suanliang 0.4.37 块内铺装/块引用的冻结参考实现。

来源：由 s5 备份的 yuanlin_qty.py（0.4.37）抽取，本机绝对路径不入发布包。
用途：只供 tests/test_landscape_equivalence.py 做新旧等价回归；
生产代码不得 import 本模块，也不得把它当作可用的算量入口。
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

def _num(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _dxf_block_ref_records(path):
    """可选 DXF 回退：读取顶层 INSERT 坐标，同名块用坐标去重后可从 P2 升为 P0/P1。

    只取模型空间顶层插入点，不展开嵌套变换，不把块定义当实例；单位不做缩放，
    计数与去重坐标只作为逐株证据。
    """
    vendor = Path(os.environ.get("CAD_SKILL_DIR", "")) / "vendor" if os.environ.get("CAD_SKILL_DIR") else None
    if not (vendor and vendor.exists()):
        vendor = Path.home() / ".codex" / "skills" / "cad-file-reader" / "vendor"
    if vendor.exists() and str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
    try:
        import ezdxf  # type: ignore
    except Exception as exc:
        return {"records": [], "warnings": [f"ezdxf 不可用：{exc}"], "insert_count": 0}
    try:
        doc = ezdxf.readfile(str(path))
    except Exception as exc:
        return {"records": [], "warnings": [f"DXF 读取失败：{exc}"], "insert_count": 0}
    recs, warnings = [], []
    try:
        for entity in doc.modelspace().query("INSERT"):
            name = str(getattr(entity.dxf, "name", "") or "").strip()
            if not name:
                continue
            try:
                pt = entity.dxf.insert
                recs.append({"kind": "INSERT", "text": name, "x": float(pt[0]), "y": float(pt[1]),
                             "layer": str(getattr(entity.dxf, "layer", "") or ""), "source": "dxf_block_ref"})
            except Exception:
                continue
            if len(recs) >= 200000:
                warnings.append("DXF INSERT 超过安全上限，已截断")
                break
    except Exception as exc:
        warnings.append(f"DXF INSERT 读取失败：{exc}")
    return {"records": recs, "warnings": warnings, "insert_count": len(recs)}


def _poly_area(poly):
    s = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def _point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _faces(segs, tol):
    """轻量环面提取：把线段端点吸附成图，按逆时针邻接追踪边界，去重取多边形（面积可正可负）。"""
    key = lambda x, y: (round(x / max(tol, 1e-9)), round(y / max(tol, 1e-9)))
    nodes, edges = {}, []
    for s in segs:
        x1, y1, x2, y2 = s
        a, b = key(x1, y1), key(x2, y2)
        if a == b:
            continue
        nodes.setdefault(a, (x1, y1))
        nodes.setdefault(b, (x2, y2))
        edges.append((a, b))
    if not nodes:
        return []
    pts, idx = nodes, list(nodes)
    pidx = {p: i for i, p in enumerate(idx)}
    adj = [[] for _ in idx]
    edges = {(pidx[a], pidx[b]) for a, b in edges}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    for i in range(len(idx)):
        adj[i].sort(key=lambda j: math.atan2(pts[idx[j]][1] - pts[idx[i]][1], pts[idx[j]][0] - pts[idx[i]][0]))
    pos = {}
    for i in range(len(idx)):
        for k, j in enumerate(adj[i]):
            pos[i, j] = k
    used, out = set(), []
    guard_max = len(idx) ** 2 + 8
    for a in range(len(idx)):
        for b in list(adj[a]):
            if (a, b) in used:
                continue
            path, cur, nx, guard = [], a, b, 0
            while (cur, nx) not in used and guard < guard_max:
                used.add((cur, nx))
                path.append(cur)
                guard += 1
                ns = adj[nx]
                k = pos.get((nx, cur))
                if k is None:
                    break
                nxt = ns[(k + 1) % len(ns)]
                cur, nx = nx, nxt
            if cur == a and nxt == b and len(path) >= 3 and len(set(path)) == len(path):
                poly = [pts[idx[i]] for i in path] + [pts[idx[a]]]
                ar = _poly_area(poly)
                if abs(ar) > 1e-6:
                    out.append((poly, ar))
    # 去重：同一边界正反追踪只保留一条（面积取绝对值由调用方处理）
    seen, res = set(), []
    for poly, ar in out:
        s = _poly_key(poly)
        if s in seen:
            continue
        seen.add(s)
        res.append((poly, ar))
    return res


def _bbox(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return [min(xs), min(ys), max(xs), max(ys)]


def _centroid(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))


def _poly_key(poly, digits=6):
    """闭合环去重键：忽略起点和方向，只保留吸附后的点集。"""
    pts = [(round(float(x), digits), round(float(y), digits)) for x, y in poly]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return tuple(sorted(pts))


def _dxf_arc_points(start_point, end_point, bulge, max_deg=10.0):
    """把 LWPOLYLINE bulge 边展开成弦端点间的圆弧点列；bulge=0 返回空。"""
    try:
        from ezdxf.math import bulge_to_arc
    except Exception:
        return []
    try:
        center, s_angle, e_angle, radius = bulge_to_arc(start_point, end_point, float(bulge))
        if radius <= 0 or not all(math.isfinite(float(v)) for v in (center[0], center[1], s_angle, e_angle, radius)):
            return []
        start_deg = math.degrees(s_angle)
        sweep = math.degrees(e_angle - s_angle)
        n = max(2, min(180, int(math.ceil(abs(sweep) / max(max_deg, 1.0)))))
        return [(center[0] + radius * math.cos(math.radians(start_deg + sweep * i / n)),
                 center[1] + radius * math.sin(math.radians(s_angle + sweep * i / n)))
                for i in range(1, n + 1)]
    except Exception:
        return []


def _dxf_arc_boundary_points(entity, max_deg=10.0):
    """ARC 边界点列（不含起点）；单独 ARC 以弦闭合后可形成 P3 候选环。"""
    try:
        cx, cy = float(entity.dxf.center.x), float(entity.dxf.center.y)
        r = float(entity.dxf.radius)
        s = float(entity.dxf.start_angle)
        e = float(entity.dxf.end_angle)
        if r <= 0 or not all(math.isfinite(v) for v in (cx, cy, r, s, e)):
            return []
        sweep = e - s
        while sweep <= 0:
            sweep += 360.0
        n = max(2, min(180, int(math.ceil(sweep / max(max_deg, 1.0)))))
        return [(cx + r * math.cos(math.radians(s + sweep * i / n)),
                 cy + r * math.sin(math.radians(s + sweep * i / n)))
                for i in range(1, n + 1)]
    except Exception:
        return []


def _dxf_hatch_boundary_points(path, max_deg=10.0):
    """HATCH 边界点列：支持 PolylinePath 与 Line/Arc EdgePath；只取边界，不读取填充值。"""
    pts = []
    if hasattr(path, 'vertices'):
        for v in getattr(path, 'vertices', []) or []:
            try:
                x, y = float(v[0]), float(v[1])
                if math.isfinite(x) and math.isfinite(y):
                    pts.append((x, y))
            except Exception:
                pass
        if len(pts) >= 3 and pts[0] != pts[-1]:
            pts.append(pts[0])
        return pts
    if not hasattr(path, 'edges'):
        return []
    for edge in getattr(path, 'edges', []) or []:
        typ = str(getattr(edge, 'EDGE_TYPE', getattr(edge, 'type', '')) or '').lower()
        try:
            if typ == 'line':
                for v in (edge.start_point, edge.end_point):
                    x, y = float(v[0]), float(v[1])
                    if math.isfinite(x) and math.isfinite(y):
                        pts.append((x, y))
            elif typ == 'arc':
                a0 = float(edge.start_angle)
                a1 = float(edge.end_angle)
                cx, cy = float(edge.center.x), float(edge.center.y)
                r = float(edge.radius)
                sweep = a1 - a0
                while sweep <= 0:
                    sweep += 360.0
                n = max(2, min(180, int(math.ceil(sweep / max(max_deg, 1.0)))))
                pts.extend((cx + r * math.cos(math.radians(a0 + sweep * i / n)),
                            cy + r * math.sin(math.radians(a0 + sweep * i / n)))
                           for i in range(n + 1))
        except Exception:
            continue
    if len(pts) >= 3 and pts[0] != pts[-1]:
        pts.append(pts[0])
    return pts


def _dxf_block_paving_segments(path, cfg):
    """可选 DXF 回退：展开 INSERT 变换，提取铺装块内闭合 LWPOLYLINE/POLYLINE/HATCH/ARC，含 bulge 圆弧。

    只处理明确命中铺装 token 的图层/块名，跳过铺装小板块等微图案；单位优先读 $INSUNITS。
    全部 DXF 回退结果强制 P3（由调用方按“DXF回退”层名判定）。
    """
    vendor = Path(os.environ.get("CAD_SKILL_DIR", "")) / "vendor" if os.environ.get("CAD_SKILL_DIR") else None
    if not (vendor and vendor.exists()):
        vendor = Path.home() / ".codex" / "skills" / "cad-file-reader" / "vendor"
    if vendor.exists() and str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
    try:
        import ezdxf  # type: ignore
    except Exception as exc:
        return {"segments": [], "layers": [], "mm_per_unit": None, "warnings": [f"ezdxf 不可用：{exc}"]}

    unit_mm = {1: 25.4, 2: 304.8, 4: 1.0, 5: 10.0, 6: 1000.0}
    tokens = [str(x).strip().lower() for x in (cfg.get("paving_layer_tokens") or []) if str(x).strip()]
    skip_tokens = ("paving slab", "paving unit", "paver", "joint", "grout", "tile")
    segs, layers, warnings = [], [], []
    seen_entities = 0
    ring_count = 0
    try:
        doc = ezdxf.readfile(str(path))
    except Exception as exc:
        return {"segments": [], "layers": [], "mm_per_unit": None, "warnings": [f"DXF 读取失败：{exc}"]}

    try:
        unit_mm_value = unit_mm.get(int(doc.header.get("$INSUNITS") or 0))
    except Exception:
        unit_mm_value = None

    def add_ring(pts, layer_label):
        nonlocal ring_count
        clean = []
        for x, y in pts:
            if len(clean) >= 2 and abs(x - clean[-2][0]) < 1e-12 and abs(y - clean[-2][1]) < 1e-12:
                clean[-1] = (x, y)
                continue
            clean.append((x, y))
        while len(clean) > 1 and abs(clean[0][0] - clean[-1][0]) < 1e-12 and abs(clean[0][1] - clean[-1][1]) < 1e-12:
            clean.pop()
        if len(clean) < 3:
            return
        for i, (x1, y1) in enumerate(clean):
            x2, y2 = clean[(i + 1) % len(clean)]
            if abs(x1 - x2) < 1e-12 and abs(y1 - y2) < 1e-12:
                continue
            segs.append([x1, y1, x2, y2])
            layers.append(layer_label)
        ring_count += 1

    def walk(layout, matrix, path_names):
        nonlocal seen_entities, ring_count
        for entity in layout:
            seen_entities += 1
            if seen_entities > 200000 or ring_count > 5000:
                if len(warnings) < 3:
                    warnings.append("DXF 实体/闭合环超过安全上限，已截断")
                return
            typ = entity.dxftype()
            if typ in ("INSERT", "MINSERT"):
                name = str(getattr(entity.dxf, "name", "") or "")
                low_name = name.lower()
                if not name or name in path_names or any(s in low_name for s in skip_tokens):
                    continue
                try:
                    block = doc.blocks.get(name)
                except Exception:
                    continue
                try:
                    insert_matrix = entity.matrix44()
                    child_matrix = insert_matrix if matrix is None else matrix @ insert_matrix
                except Exception:
                    child_matrix = matrix
                walk(block, child_matrix, path_names + (name,))
                continue
            owner = " / ".join(path_names)
            entity_layer = str(entity.dxf.layer or "")
            effective_layer = entity_layer if entity_layer not in ("", "0") else (path_names[-1] if path_names else entity_layer)
            current_block = path_names[-1] if path_names else ""
            hay = f"{current_block} {entity_layer} {effective_layer}".lower()
            if not any(token in hay for token in tokens):
                continue
            if any(s in owner.lower() for s in skip_tokens):
                continue

            def transform_point(x, y):
                if matrix is not None:
                    p = matrix.transform((float(x), float(y), 0.0))
                    return float(p[0]), float(p[1])
                return float(x), float(y)

            def transformed(points):
                return [transform_point(x, y) for x, y in points]

            pts = []
            ring_ready = False
            try:
                if typ == "LWPOLYLINE":
                    raw = list(entity.get_points("xyb"))
                    for i, (x, y, bulge) in enumerate(raw):
                        pts.append((float(x), float(y)))
                        b = float(bulge or 0.0)
                        if abs(b) > 1e-9:
                            nx, ny = raw[(i + 1) % len(raw)][:2]
                            pts.extend(transformed([]) if False else _dxf_arc_points((float(x), float(y)), (float(nx), float(ny)), b))
                    if getattr(entity, "closed", False):
                        ring_ready = True
                    elif len(pts) >= 3 and abs(pts[0][0] - pts[-1][0]) < 1e-9 and abs(pts[0][1] - pts[-1][1]) < 1e-9:
                        ring_ready = True
                elif typ == "POLYLINE" and getattr(entity, "is_closed", False):
                    vertices = list(entity.vertices)
                    for i, v in enumerate(vertices):
                        loc = v.dxf.location
                        pts.append((float(loc.x), float(loc.y)))
                        b = float(getattr(v.dxf, "bulge", 0.0) or 0.0)
                        if abs(b) > 1e-9:
                            nv = vertices[(i + 1) % len(vertices)].dxf.location
                            pts.extend(_dxf_arc_points((float(loc.x), float(loc.y)), (float(nv.x), float(nv.y)), b))
                    ring_ready = True
                elif typ == "HATCH":
                    for bp in entity.paths or []:
                        hp = _dxf_hatch_boundary_points(bp)
                        if len(hp) >= 3:
                            pts = transformed(hp)
                            add_ring(pts, f"（DXF回退）HATCH {owner} [{entity_layer or effective_layer}]" if owner else f"（DXF回退）HATCH [{entity_layer or effective_layer}]")
                    continue
                elif typ == "ARC":
                    ap = _dxf_arc_boundary_points(entity)
                    if ap:
                        start = (float(entity.dxf.center.x) + float(entity.dxf.radius) * math.cos(math.radians(float(entity.dxf.start_angle))),
                                 float(entity.dxf.center.y) + float(entity.dxf.radius) * math.sin(math.radians(float(entity.dxf.start_angle))))
                        pts = [transform_point(*start)] + transformed(ap) + [transform_point(*start)]
                        add_ring(pts, f"（DXF回退）ARC {owner} [{entity_layer or effective_layer}]" if owner else f"（DXF回退）ARC [{entity_layer or effective_layer}]")
                    continue
            except Exception as exc:
                if len(warnings) < 3:
                    warnings.append(f"DXF {typ} 边界展开失败：{exc}")
                continue
            if not ring_ready or len(pts) < 3:
                continue
            pts = transformed(pts)
            layer_label = f"（DXF回退）{owner} [{entity_layer or effective_layer}]" if owner else f"（DXF回退）{entity_layer or effective_layer or '未知铺装图层'}"
            add_ring(pts, layer_label)

    try:
        walk(doc.modelspace(), None, ())
    except Exception as exc:
        warnings.append(f"DXF 块几何展开失败：{exc}")
    return {"segments": segs, "layers": layers, "mm_per_unit": unit_mm_value, "warnings": warnings}
