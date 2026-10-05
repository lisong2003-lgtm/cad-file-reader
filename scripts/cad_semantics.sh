#!/usr/bin/env bash
# P2/P3 图层与块语义候选入口。
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_cad.sh" cad_semantics "$@"
