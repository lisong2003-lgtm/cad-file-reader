#!/usr/bin/env bash
# 图例知识表匹配候选入口（轻量词库，不输出工程量）。
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_cad.sh" cad_legend "$@"
