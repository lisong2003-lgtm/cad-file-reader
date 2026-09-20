#!/usr/bin/env python3
"""Read DWG/DXF CAD files and emit structured or human-readable summaries."""

from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional


# ---- 内存闸（2026-08-31 加，整档 ezdwg/ezdxf 解析会吃 GB 级内存，曾导致系统卡死被长按电源键）----
DEFAULT_CAP_MB = 4096       # 单进程硬上限（RLIMIT_AS）：超了就 MemoryError，不拖垮整机
DEFAULT_MAX_FILE_MB = 20    # 入口大小闸：超过即拒绝整档解析，改走 scripts/cad_scan.sh 低内存路径（本机图纸 20~75MB 常见）


def apply_mem_cap(cap_mb: int) -> str:
    """macOS 没有可用的 RLIMIT_AS，改用进程内看门狗（见 mem_guard.py）。"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import mem_guard
        mem_guard.start(cap_mb)
        return "watchdog:%dMB" % cap_mb
    except Exception as exc:
        return "watchdog-failed:%s" % exc


def peak_rss_mb() -> int:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(rss / 1048576) if sys.platform == "darwin" else int(rss / 1024)


VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor"
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))


def _file_meta(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "file_name": path.name,
        "size_bytes": stat.st_size,
        "modified": stat.st_mtime,
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "x") and hasattr(value, "y"):
        z = getattr(value, "z", 0)
        return [value.x, value.y, z]
    return str(value)


def _layer_flags(layer: Any) -> dict[str, Any]:
    flags: dict[str, Any] = {}
    for output_name, method_name in (
        ("frozen", "is_frozen"),
        ("off", "is_off"),
        ("locked", "is_locked"),
    ):
        fn = getattr(layer, method_name, None)
        if callable(fn):
            try:
                flags[output_name] = bool(fn())
            except Exception:
                pass
    return flags


def _header_value(doc: Any, key: str) -> Any:
    try:
        if key in doc.header:
            return _jsonable(doc.header.get(key))
    except Exception:
        pass
    return None


def _raw_dwg_layers(path: Path) -> tuple[list[dict[str, Any]], dict[int, str]]:
    try:
        import ezdwg
    except ImportError:
        return [], {}

    name_by_handle: dict[int, str] = {}
    layers: list[dict[str, Any]] = []
    try:
        for handle, name in ezdwg.raw.decode_layer_names(str(path)) or []:
            name_by_handle[handle] = str(name or "")
            layers.append(
                {
                    "handle": handle,
                    "name": str(name or ""),
                    "color": None,
                    "true_color": None,
                    "linetype": "",
                    "frozen": None,
                    "off": None,
                    "locked": None,
                }
            )
    except Exception:
        return [], {}

    try:
        for handle, color, true_color in ezdwg.raw.decode_layer_colors(str(path)) or []:
            for layer in layers:
                if layer["handle"] == handle:
                    layer["color"] = _jsonable(color)
                    layer["true_color"] = _jsonable(true_color)
    except Exception:
        pass
    return layers, name_by_handle


def _raw_dwg_blocks(path: Path) -> list[dict[str, Any]]:
    try:
        import ezdwg

        names = ezdwg.raw.decode_block_header_names(str(path)) or []
    except Exception:
        return []

    blocks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for handle, name in names:
        block_name = str(name or "")
        if block_name and block_name not in seen:
            seen.add(block_name)
            blocks.append({"name": block_name, "handle": handle, "description": "", "base_point": None})
    return blocks


def read_dwg_direct(path: Path, max_text: int) -> Optional[dict[str, Any]]:
    try:
        import ezdwg
    except ImportError:
        return None

    try:
        doc = ezdwg.read(str(path))
    except Exception as exc:
        return {"ok": False, "error": f"ezdwg could not read DWG: {exc}"}

    layers, layer_name_by_handle = _raw_dwg_layers(path)
    entity_counts: dict[str, int] = {}
    layer_counts: dict[str, int] = {}
    text_items: list[dict[str, Any]] = []
    insert_names: set[str] = set()

    try:
        entities = list(doc.modelspace().iter_entities())
    except Exception:
        try:
            entities = list(
                doc.modelspace().query(
                    "LINE LWPOLYLINE ARC CIRCLE ELLIPSE POINT TEXT MTEXT DIMENSION INSERT MINSERT HATCH SPLINE"
                )
            )
        except Exception as exc:
            return {"ok": False, "error": f"ezdwg could not decode DWG entities: {exc}"}

    for entity in entities:
        dxftype = str(getattr(entity, "dxftype", ""))
        entity_counts[dxftype] = entity_counts.get(dxftype, 0) + 1
        dxf = getattr(entity, "dxf", {}) or {}
        layer_handle = dxf.get("layer_handle")
        default_layer = next(iter(layer_name_by_handle.values()), "0") if layer_name_by_handle else "0"
        if layer_handle in (None, 0):
            layer_name = default_layer or "0"
        else:
            layer_name = layer_name_by_handle.get(layer_handle, f"handle:{layer_handle}")
        layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1

        if dxftype in ("INSERT", "MINSERT"):
            insert_name = dxf.get("name")
            if insert_name:
                insert_names.add(str(insert_name))

        if dxftype in ("TEXT", "MTEXT") and len(text_items) < max_text:
            text = str(dxf.get("text") or dxf.get("raw_text") or "").strip()
            if text:
                text_items.append(
                    {
                        "space": "Model",
                        "layer": layer_name,
                        "type": dxftype,
                        "text": text,
                        "handle": str(getattr(entity, "handle", "") or ""),
                    }
                )

    try:
        header = doc.header_variables() or {}
    except Exception:
        header = {}

    result: dict[str, Any] = {
        "ok": True,
        "format": "DWG",
        "version": str(getattr(doc, "version", "") or ""),
        "header": {
            "$ACADVER": str(getattr(doc, "version", "") or ""),
            "$INSUNITS": header.get("insunits"),
            "$EXTMIN": header.get("extmin"),
            "$EXTMAX": header.get("extmax"),
            "$LTSCALE": header.get("ltscale"),
        },
        "layers": layers,
        "layer_counts": dict(sorted(layer_counts.items(), key=lambda item: -item[1])),
        "blocks": _raw_dwg_blocks(path),
        "block_references": sorted(insert_names),
        "text": text_items,
        "text_count_total": sum(
            count for dxftype, count in entity_counts.items() if dxftype in ("TEXT", "MTEXT")
        ),
        "entity_counts": dict(sorted(entity_counts.items(), key=lambda item: -item[1])),
        "direct_dwg_reader": "ezdwg",
    }
    return result


def _entity_text(entity: Any) -> str:
    if entity.dxftype() == "MTEXT":
        plain = getattr(entity, "plain_text", None)
        if callable(plain):
            try:
                return plain()
            except Exception:
                pass
    return str(getattr(entity.dxf, "text", "") or "")


def read_dxf(path: Path, max_text: int) -> dict[str, Any]:
    try:
        import ezdxf
    except ImportError:
        return {"ok": False, "error": "ezdxf is not installed; run pip install ezdxf or restore the skill vendor directory."}

    try:
        doc = ezdxf.readfile(str(path))
    except Exception as exc:
        return {"ok": False, "error": f"Cannot parse DXF: {exc}"}

    entity_counts: dict[str, int] = {}
    layer_counts: dict[str, int] = {}
    text_items: list[dict[str, Any]] = []
    insert_names: set[str] = set()

    def scan_space(space: Any, space_name: str) -> None:
        for entity in space:
            dxftype = entity.dxftype()
            entity_counts[dxftype] = entity_counts.get(dxftype, 0) + 1
            layer = str(getattr(entity.dxf, "layer", "0") or "0")
            layer_counts[layer] = layer_counts.get(layer, 0) + 1

            if dxftype == "INSERT":
                insert_names.add(str(getattr(entity.dxf, "name", "") or ""))

            if dxftype in ("TEXT", "MTEXT", "ATTRIB", "ATTDEF") and len(text_items) < max_text:
                text = _entity_text(entity).strip()
                if text:
                    text_items.append(
                        {
                            "space": space_name,
                            "layer": layer,
                            "type": dxftype,
                            "text": text,
                            "handle": str(getattr(entity.dxf, "handle", "") or ""),
                        }
                    )

    scan_space(doc.modelspace(), "Model")
    for layout_name in doc.layouts.names():
        if layout_name.lower() != "model":
            try:
                scan_space(doc.layout(layout_name), layout_name)
            except Exception:
                pass

    layers = []
    for layer in doc.layers:
        layers.append(
            {
                "name": str(layer.dxf.name),
                "color": _jsonable(getattr(layer.dxf, "color", None)),
                "linetype": str(getattr(layer.dxf, "linetype", "") or ""),
                **_layer_flags(layer),
            }
        )

    blocks = []
    for block in doc.blocks:
        record = getattr(block, "block_record", None)
        base_point = None
        if record is not None:
            base_point = _jsonable(getattr(record.dxf, "base_point", None))
        blocks.append(
            {
                "name": str(block.name),
                "description": str(getattr(block, "description", "") or ""),
                "base_point": base_point,
            }
        )

    header_keys = [
        "$ACADVER",
        "$INSUNITS",
        "$DWGCODEPAGE",
        "$EXTMIN",
        "$EXTMAX",
        "$TDCREATE",
        "$TDUPDATE",
        "$LTSCALE",
    ]
    header = {key: _header_value(doc, key) for key in header_keys}

    result: dict[str, Any] = {
        "ok": True,
        "format": "DXF",
        "version": str(doc.dxfversion or ""),
        "header": header,
        "layers": layers,
        "layer_counts": dict(sorted(layer_counts.items(), key=lambda item: -item[1])),
        "blocks": blocks,
        "block_references": sorted(insert_names),
        "text": text_items,
        "text_count_total": sum(
            count for dxftype, count in entity_counts.items() if dxftype in ("TEXT", "MTEXT", "ATTRIB", "ATTDEF")
        ),
        "entity_counts": dict(sorted(entity_counts.items(), key=lambda item: -item[1])),
    }
    result.update(_file_meta(path))
    return result


def _find_oda_converter() -> Optional[str]:
    candidates = [
        "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
        "/Applications/ODAFileConverter/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
        str(Path.home() / "Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter"),
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return shutil.which("ODAFileConverter")


def _convert_with_ezdwg(src: Path, outdir: Path) -> tuple[Optional[Path], str]:
    try:
        from ezdwg.convert import to_dxf
    except Exception as exc:
        return None, f"ezdwg conversion unavailable: {exc}"
    try:
        out = outdir / (src.stem + ".dxf")
        result = to_dxf(str(src), str(out), dxf_version="R2010")
        dxf_path = Path(result.output_path)
        if dxf_path.exists():
            return dxf_path, (
                f"Converted with ezdwg.to_dxf "
                f"(written {result.written_entities}/{result.total_entities})"
            )
    except Exception as exc:
        return None, f"ezdwg conversion failed: {exc}"
    return None, "ezdwg conversion returned no output"


def _convert_with_dwg2dxf(exe: str, src: Path, outdir: Path) -> Optional[Path]:
    output = outdir / (src.stem + ".dxf")
    commands = [
        [exe, "-o", str(output), str(src)],
        [exe, str(src)],
    ]
    for command in commands:
        try:
            subprocess.run(command, cwd=str(outdir), timeout=120, check=False, capture_output=True)
        except Exception:
            continue
        if output.exists():
            return output
        dxf_files = list(outdir.glob("*.dxf"))
        if dxf_files:
            return dxf_files[0]
    return None


def _convert_with_oda(exe: str, src: Path, outdir: Path) -> Optional[Path]:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            in_dir = Path(tmp)
            shutil.copy2(src, in_dir / src.name)
            command = [exe, str(in_dir), str(outdir), "ACAD2018", "DXF", "0", "1", src.name]
            subprocess.run(command, timeout=180, check=False, capture_output=True)
    except Exception:
        pass
    dxf_files = list(outdir.glob("*.dxf"))
    return dxf_files[0] if dxf_files else None


def convert_dwg_to_dxf(src: Path) -> tuple[Optional[Path], str]:
    with tempfile.TemporaryDirectory(prefix="cad-reader-") as tmp:
        dxf, note = _convert_with_ezdwg(src, Path(tmp))
        if dxf:
            return dxf, note

    dwg2dxf = shutil.which("dwg2dxf")
    oda = _find_oda_converter()

    if dwg2dxf:
        with tempfile.TemporaryDirectory(prefix="cad-reader-") as tmp:
            dxf = _convert_with_dwg2dxf(dwg2dxf, src, Path(tmp))
            if dxf:
                return dxf, f"Converted with dwg2dxf ({dwg2dxf})"

    if oda:
        with tempfile.TemporaryDirectory(prefix="cad-reader-") as tmp:
            dxf = _convert_with_oda(oda, src, Path(tmp))
            if dxf:
                return dxf, f"Converted with ODAFileConverter ({oda})"

    return None, "No DWG converter found"


def render_svg(src: Path, out_dir: Path, stem: Optional[str] = None) -> tuple[Optional[str], str]:
    try:
        import ezdxf
        from ezdxf.addons.drawing import Frontend, RenderContext, layout
        from ezdxf.addons.drawing.svg import SVGBackend
    except Exception as exc:
        return None, f"SVG renderer is unavailable: {exc}"

    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        doc = ezdxf.readfile(str(src))
        space = doc.modelspace()
        try:
            if len(space) == 0:
                for name in doc.layouts.names():
                    if name.lower() != "model":
                        space = doc.layout(name)
                        break
        except Exception:
            pass

        backend = SVGBackend()
        frontend = Frontend(RenderContext(doc), backend)
        frontend.draw_layout(space)
        page = layout.Page(1000, 1000, units=layout.Units.mm)
        target = out_dir / ((stem or src.stem) + "-preview.svg")
        target.write_text(backend.get_string(page), encoding="utf-8")
        return str(target), ""
    except Exception as exc:
        return None, f"SVG render failed: {exc}"


def render_dwg_svg(src: Path, out_dir: Path) -> tuple[Optional[str], str]:
    try:
        import ezdwg

        doc = ezdwg.read(str(src))
        with tempfile.TemporaryDirectory(prefix="cad-dwg-render-") as tmp:
            dxf_path = Path(tmp) / "render.dxf"
            doc.export_dxf(str(dxf_path))
            return render_svg(dxf_path, out_dir, stem=src.stem)
    except Exception as exc:
        return None, f"DWG SVG render failed: {exc}"


def _detect_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".dwg":
        return "DWG"
    if suffix in (".dxf", ".dwt"):
        return "DXF"
    try:
        with open(path, "rb") as handle:
            head = handle.read(32)
    except Exception:
        return "UNKNOWN"
    if head.startswith(b"AC"):
        return "DWG"
    if b"SECTION" in head or b"\x00SECT" in head:
        return "DXF"
    return "UNKNOWN"


def process_file(path: Path, max_text: int, render: bool, render_dir: Path) -> dict[str, Any]:
    kind = _detect_kind(path)
    if kind == "DWG":
        direct = read_dwg_direct(path, max_text)
        if direct and direct.get("ok"):
            result = direct
            direct_error = None
        else:
            direct_error = direct.get("error") if direct else None
            dxf, note = convert_dwg_to_dxf(path)
            if dxf is None:
                error = note
                if direct_error:
                    error = f"{direct_error} {note}"
                result = {
                    "ok": False,
                    "format": "DWG",
                    "error": error,
                    "fix": "Install LibreDWG (brew install libredwg) or ODAFileConverter, or save the DWG as DXF from CAD software.",
                }
            else:
                result = read_dxf(dxf, max_text)
                result["format"] = "DWG (converted to DXF)"
                result["conversion"] = note
                if direct_error:
                    result["direct_error"] = direct_error
    elif kind == "DXF":
        result = read_dxf(path, max_text)
    else:
        result = {"ok": False, "format": "UNKNOWN", "error": "Unrecognized file format; expected .dwg, .dxf, or .dwt."}

    result.update(_file_meta(path))

    if render:
        if kind == "DWG" and result.get("ok"):
            preview, render_note = render_dwg_svg(path, render_dir)
        else:
            preview, render_note = render_svg(path, render_dir)
        result["preview_svg"] = preview
        result["render_note"] = render_note
    return result


def _collect_files(paths: list[str], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            pattern = "**/*" if recursive else "*"
            files.extend(p for p in path.glob(pattern) if p.suffix.lower() in (".dwg", ".dxf", ".dwt"))
        elif path.exists():
            files.append(path)
    return sorted(dict.fromkeys(files))


def format_text(result: dict[str, Any]) -> str:
    lines = [f"File: {result.get('path', '')}"]
    if not result.get("ok"):
        lines.append(f"Status: ERROR - {result.get('error', 'unknown')}")
        if result.get("fix"):
            lines.append(f"Fix: {result['fix']}")
        return "\n".join(lines)

    lines.append(f"Format: {result.get('format', '')} | Version: {result.get('version', '')}")
    lines.append(f"Size: {result.get('size_bytes', 0)} bytes")

    layers = result.get("layers") or []
    if layers:
        names = [layer.get("name", "") for layer in layers]
        preview = ", ".join(names[:40])
        if len(names) > 40:
            preview += f" (+{len(names) - 40} more)"
        lines.append(f"Layers ({len(names)}): {preview}")

    layer_counts = result.get("layer_counts") or {}
    if layer_counts:
        top = ", ".join(f"{name}={count}" for name, count in list(layer_counts.items())[:20])
        lines.append(f"Entities by layer: {top}")

    text = result.get("text") or []
    if text:
        lines.append(f"Text ({result.get('text_count_total', len(text))} total, {len(text)} shown):")
        for item in text[:20]:
            lines.append(f"  [{item['space']}] {item['text']}")

    blocks = result.get("blocks") or []
    if blocks:
        lines.append(f"Blocks ({len(blocks)}): {', '.join(block['name'] for block in blocks[:30])}")

    entities = result.get("entity_counts") or {}
    if entities:
        top = ", ".join(f"{name}={count}" for name, count in list(entities.items())[:25])
        lines.append(f"Entity types: {top}")

    if result.get("preview_svg"):
        lines.append(f"Preview SVG: {result['preview_svg']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read DWG/DXF CAD files and summarize their contents.")
    parser.add_argument("paths", nargs="+", help="CAD file(s) or folder(s)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    parser.add_argument("--output", help="Write the summary to this file")
    parser.add_argument("--max-text", type=int, default=500, help="Maximum text entities to include (default: 500)")
    parser.add_argument("--render", action="store_true", help="Also render an SVG preview with ezdxf")
    parser.add_argument("--render-dir", default=".", help="Directory for SVG previews (default: current directory)")
    parser.add_argument("--recursive", action="store_true", help="Search folders recursively")
    parser.add_argument("--cap-mb", dest="cap_mb", type=int, default=DEFAULT_CAP_MB,
                        help="单进程内存硬上限 MB（0=不限，默认 4096）")
    parser.add_argument("--max-file-mb", dest="max_file_mb", type=int, default=DEFAULT_MAX_FILE_MB,
                        help="入口大小闸：超过就不做整档解析（默认 40）")
    parser.add_argument("--allow-big", dest="allow_big", action="store_true",
                        help="明知很大仍强行整档解析（配合 --cap-mb 使用）")
    args = parser.parse_args()
    cap_state = apply_mem_cap(args.cap_mb)

    files = _collect_files(args.paths, args.recursive)
    if not files:
        print("No .dwg, .dxf, or .dwt files found.")
        return 1

    render_dir = Path(args.render_dir)
    results: list[dict[str, Any]] = []
    for path in files:
        size = path.stat().st_size
        mb = size / 1048576.0
        if mb > args.max_file_mb and not args.allow_big:
            results.append({
                "ok": False,
                **_file_meta(path),
                "error": f"内存闸：文件 {mb:.0f}MB 超过入口上限 {args.max_file_mb}MB，已拒绝整档解析",
                "hint": "大图纸请用 scripts/cad_scan.sh（只解文字/图层/块名，低内存）；"
                        "确需整档解析再加 --allow-big",
            })
            continue
        try:
            results.append(process_file(path, args.max_text, args.render, render_dir))
        except MemoryError:
            results.append({
                "ok": False,
                **_file_meta(path),
                "error": f"内存闸：解析超出硬上限 {args.cap_mb}MB 已中断（当前峰值 {peak_rss_mb()}MB）",
                "hint": "改用 scripts/cad_scan.sh，或用 --cap-mb 提高上限（别超过物理内存一半）",
            })
    print(f"[cad内存闸] cap={cap_state} 已用峰值 RSS={peak_rss_mb()}MB", file=sys.stderr)
    output: str
    if args.json:
        output = json.dumps(results if len(results) > 1 else results[0], indent=2, ensure_ascii=False)
    else:
        output = "\n\n".join(format_text(result) for result in results)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"Written: {output_path}")
    else:
        print(output)

    return 0 if all(result.get("ok", False) for result in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
