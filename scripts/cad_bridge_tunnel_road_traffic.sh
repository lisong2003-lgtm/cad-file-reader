#!/usr/bin/env bash
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_cad.sh" cad_deep_geometry --pack bridge_tunnel_road_traffic "$@"
