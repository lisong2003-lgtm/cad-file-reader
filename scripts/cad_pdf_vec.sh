#!/usr/bin/env bash
# 矢量 PDF 原生文字坐标提取（供 PDF 识图分流复核）。
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY=""
for candidate in \
  "$HOME"/.codex/skills/pdf-inspector/.venv/bin/python \
  "$HOME"/.cache/codex-runtimes/*/dependencies/python/bin/python3
do
  if [[ -n "${candidate}" && -x "${candidate}" ]]; then
    VENV_PY="${candidate}"
    break
  fi
done
if [[ -z "${VENV_PY}" ]]; then
  echo "pdf-inspector/system Python 3 not found; cannot extract PDF vector coords." >&2
  exit 1
fi
exec "${VENV_PY}" "${SKILL_DIR}/scripts/cad_pdf_vec.py" "$@"
