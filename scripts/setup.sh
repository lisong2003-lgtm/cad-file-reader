#!/usr/bin/env bash
# 一站式安装（SkillHub 轻量包 / 缺依赖时使用）：
#   1) 检查 Python 3.10+
#   2) 检查并补齐 vendor（install_vendor.sh，幂等）
#   3) 生成/更新本机 .env 供 PYTHONPATH 使用（可选）
#   4) 依赖检查（deps_check.sh --minimal）并提示一条示例命令
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# SkillHub 下载包可能丢失可执行位：先补回（setup 支持 bash scripts/setup.sh 调用）
if [ -d "$SKILL_DIR/scripts" ]; then
  find "$SKILL_DIR/scripts" -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} + 2>/dev/null || true
fi
cd "$SKILL_DIR"

echo "=== 1/4 Python 检查 ==="
PYTHON_BIN=""
for candidate in \
  "$HOME"/.cache/codex-runtimes/*/dependencies/python/bin/python3 \
  "$(command -v python3 || true)"; do
  if [[ -n "${candidate}" && -x "${candidate}" ]]; then PYTHON_BIN="${candidate}"; break; fi
done
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "❌ 未找到 python3，需要 Python 3.10+" >&2; exit 1
fi
echo "  使用 python：$PYTHON_BIN"
INPUT0="$($PYTHON_BIN -c 'import sys; print(1 if sys.version_info>=(3,10) else 0)')"
if [[ "$INPUT0" != "1" ]]; then echo "❌ 需要 Python 3.10+（当前 $($PYTHON_BIN -V 2>&1)）" >&2; exit 1; fi

echo "=== 2/4 vendor 依赖 ==="
if [ ! -d vendor/ezdwg ] || [ ! -d vendor/ezdxf ] || [ ! -d vendor/fontTools ]; then
  bash scripts/install_vendor.sh
else
  echo "  vendor 已存在，跳过（强制重装：export CAD_FORCE_INSTALL=1 后运行 scripts/install_vendor.sh）"
fi

echo "=== 3/4 本机环境变量（可选 .env）==="
ENV_FILE="$SKILL_DIR/.env"
if [ -f "$ENV_FILE" ] && grep -q "^PYTHONPATH=" "$ENV_FILE"; then
  echo "  .env 已存在，未变更"
else
  cat > "$ENV_FILE" <<EOF
# 由 scripts/setup.sh 生成；供未走 run_cad.sh 自举的手工调用使用
PYTHONPATH="$SKILL_DIR/vendor"
EOF
  echo "  已生成 $ENV_FILE"
fi

echo "=== 4/4 自检 ==="
bash scripts/deps_check.sh --minimal || true
echo ""
echo "✅ 安装完成。示例：bash scripts/demo.sh"
