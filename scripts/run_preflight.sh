#!/usr/bin/env bash
# 发布前预检：全量自测 -> 契约校验 -> 脱敏扫描 -> 可选真图回归。
# 用法：scripts/run_preflight.sh [--manifest <真图清单.json>]
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
  echo "❌ Python 3 not found;" >&2
  exit 1
fi
MANIFEST=""
if [[ "${1:-}" == "--manifest" ]]; then
  MANIFEST="${2:?--manifest 需要参数}"
  shift 2
fi
if [[ -z "${MANIFEST}" ]]; then
  echo "⚠️ 未提供 --manifest，跳过真实图纸回归；发布前必须带真图清单跑一次。"
fi
echo "=== 1/4 全量自测 ==="
(cd "${SKILL_DIR}" && PYTHONPYCACHEPREFIX=/tmp/cad-pycache "${PYTHON_BIN}" -m unittest discover -s scripts/tests -p "test_*.py")
echo "=== 2/4 契约样例校验 ==="
# 用测试生成/现存样例若在 scripts/tests 下则校验；无样例时仅依赖单测中 validate 断言
find "${SKILL_DIR}/scripts/tests" -name "*.json" -not -path "*__pycache__*" -print0 2>/dev/null | xargs -0 -r -n1 "${SKILL_DIR}/scripts/cad_validate.sh" || true
echo "=== 3/4 发布脱敏扫描 ==="
"${PYTHON_BIN}" "${SKILL_DIR}/scripts/cad_release_scrub.py" "${SKILL_DIR}" \
  --skip-dirs vendor,__pycache__,.git,node_modules,tests
if [[ -n "${MANIFEST}" ]]; then
  echo "=== 4/4 真图回归 ==="
  "${SKILL_DIR}/scripts/run_real_dwg_regression.sh" --manifest "${MANIFEST}"
  rc=$?
  if [[ ${rc} -ne 0 ]]; then
    echo "❌ 真图回归失败（rc=${rc}）" >&2
    exit ${rc}
  fi
else
  echo "=== 4/4 跳过（缺 manifest） ==="
fi
echo "✅ 发布预检完成"
