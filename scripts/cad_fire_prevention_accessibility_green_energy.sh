#!/usr/bin/env bash
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_cad.sh" cad_deep_geometry --pack fire_prevention_accessibility_green_energy "$@"
