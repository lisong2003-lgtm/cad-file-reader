#!/usr/bin/env bash
# 通用入口：run_cad.sh <cad_scan|read_cad> [参数...]
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN=""
for candidate in \
  "$HOME"/.cache/codex-runtimes/*/dependencies/python/bin/python3 \
  "$(command -v python3 || true)"
do
  if [[ -n "${candidate}" && -x "${candidate}" ]]; then
    PYTHON_BIN="${candidate}"
    break
  fi
done
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "Python 3 not found; cannot run CAD reader." >&2
  exit 1
fi
# 内存闸（2026-08-31）：macOS 无 RLIMIT_AS/ulimit -v，硬保护在 mem_guard.py 看门狗。
: "${CAD_MEM_LIMIT_MB:=4096}"
export CAD_MEM_LIMIT_MB
export PYTHONPATH="${SKILL_DIR}/vendor${PYTHONPATH:+:${PYTHONPATH}}"
SCRIPT_NAME="${1:?用法: run_cad.sh <cad_scan|read_cad> [参数...]}"
shift
exec "${PYTHON_BIN}" "${SKILL_DIR}/scripts/${SCRIPT_NAME}.py" "$@"
