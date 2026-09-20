#!/usr/bin/env bash
# 低内存快速路径：只解文字/图层/块名，不建整棵实体树。
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_cad.sh" cad_scan "$@"
