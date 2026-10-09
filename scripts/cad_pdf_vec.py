#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取矢量 PDF 的原生文字坐标候选。

只从 PDF 原生字节中提取文字位置（x/y/width/height/font/page），不识别、
不渲染、不输出量、不转换 DXF。供 cad_pdf_ocr.py 在 source_format=pdf_vector
时补充 bbox 证据；最终契约仍为 final_quantity=false 的识图候选。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import pdf_inspector
except ImportError:
    # 由 pdf-inspector 技能的 .venv 运行时才可导入
    sys.stderr.write("pdf_inspector 未安装（需要 pdf-inspector 技能的 venv）\n")
    raise


def extract(pdf: Path, pages: list[int] | None = None) -> list[dict]:
    page_arg: list[int] | None = None
    if pages:
        page_arg = [int(p) for p in pages if p > 0]
    items = pdf_inspector.extract_text_with_positions(str(pdf), pages=page_arg)
    out: list[dict] = []
    for item in items or []:
        text = str(getattr(item, "text", "") or "").strip()
        if not text:
            continue
        out.append({
            "page": int(getattr(item, "page", 1) or 1),
            "text": text[:240],
            "x": round(float(getattr(item, "x", 0) or 0), 3),
            "y": round(float(getattr(item, "y", 0) or 0), 3),
            "width": round(float(getattr(item, "width", 0) or 0), 3),
            "height": round(float(getattr(item, "height", 0) or 0), 3),
            "font": getattr(item, "font", None),
            "font_size": round(float(getattr(item, "font_size", 0) or 0), 3) if getattr(item, "font_size", None) not in (None, "", 0) else None,
            "is_bold": bool(getattr(item, "is_bold", False)),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="矢量 PDF 原生文字坐标提取")
    ap.add_argument("pdf", help="PDF 文件路径")
    ap.add_argument("--pages", default="", help="逗号分隔页号；省略则全部")
    ap.add_argument("--json", default="-", help="输出 JSON 路径，默认 stdout")
    args = ap.parse_args()
    pdf = Path(args.pdf)
    if not pdf.exists():
        print(json.dumps({"error": f"PDF 不存在: {pdf}"}, ensure_ascii=False), file=sys.stderr)
        return 1
    try:
        pages = [int(x) for x in args.pages.split(",") if x.strip().isdigit()] if args.pages else None
        items = extract(pdf, pages)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": f"矢量文字坐标提取失败: {exc}"}, ensure_ascii=False), file=sys.stderr)
        return 1
    payload = {
        "schema": "cad-file-reader/pdf-vector-text-coords/v1",
        "source_file": str(pdf),
        "count": len(items),
        "items": items,
        "boundary": "只输出 PDF 原生文字坐标候选，final_quantity=false；坐标单位为 PDF 点，不参与测量。",
    }
    if args.json and args.json != "-":
        Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
