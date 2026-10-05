#!/usr/bin/env bash
# 图纸说明与规则解读入口：需要 cad_scan 生成的 JSON。
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_cad.sh" cad_interpret "$@"
