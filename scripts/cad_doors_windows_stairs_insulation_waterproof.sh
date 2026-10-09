#!/usr/bin/env bash
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_cad.sh" cad_deep_geometry --pack doors_windows_stairs_insulation_waterproof "$@"
