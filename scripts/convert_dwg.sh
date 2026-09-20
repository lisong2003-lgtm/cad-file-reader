#!/usr/bin/env bash
# Convert DWG/DWT to DXF using vendored ezdwg.
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_cad.sh" convert_dwg "$@"
