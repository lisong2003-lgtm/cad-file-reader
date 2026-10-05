#!/usr/bin/env bash
# P5 图纸对比候选入口。
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_cad.sh" cad_compare "$@"
