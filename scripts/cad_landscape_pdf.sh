#!/usr/bin/env bash
# PDF → 园林识图候选
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_cad.sh" cad_landscape_pdf "$@"
