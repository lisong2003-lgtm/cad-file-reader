#!/usr/bin/env bash
# 为 SkillHub 轻量包补齐 vendor 依赖：优先本包版本的 GitHub Release，
# 拿不到就退回任一可用 Release，最后兜底 pip。
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${CAD_FILE_READER_REPO:-lisong2003-lgtm/cad-file-reader}"
MANIFEST="$SKILL_DIR/manifest.json"
PKG_VER="$(sed -n 's/.*"version"[ ]*:[ ]*"\([^"]*\)".*/\1/p' "$MANIFEST" 2>/dev/null | head -1)"
WANT="${CAD_FILE_READER_VERSION:-${PKG_VER:-0.18.0}}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

fetch() {
  local url="https://github.com/${REPO}/releases/download/v$1/cad-file-reader-full-$1.zip"
  echo "尝试 $url" >&2
  curl -sL --http1.1 --fail "$url" -o "$TMP/full.zip" || return 1
  unzip -oq "$TMP/full.zip" "*/vendor/*" -d "$TMP" || return 1
  [ -d "$TMP/cad-file-reader/vendor" ] || [ -n "$(find "$TMP" -type d -name vendor -print -quit)" ] || return 1
}

if fetch "$WANT"; then
  :
else
  echo "本包版本 v${WANT} 的完整包不可用，改从可用 Release 取依赖…" >&2
  ok=0
  for alt in 0.2.3 0.2.0 0.1.0; do
    if [ "$alt" != "$WANT" ] && fetch "$alt"; then ok=1; break; fi
  done
  if [ "$ok" = 0 ]; then
    cat >&2 <<'MSG'
GitHub Release 取不到依赖。请改用 PyPI：
  python3 -m pip install "ezdwg==0.12.6" "ezdxf==1.4.4" fonttools pyparsing numpy
再把安装目录下的 PYTHONPATH 指过去，或直接 export PYTHONPATH=<含这些包的目录>
MSG
    exit 3
  fi
fi

DEST="$SKILL_DIR/vendor"
if [ -d "$DEST" ]; then find "$DEST" -depth -delete; fi
SRC="$(find "$TMP" -type d -name vendor -print -quit)"
cp -R "$SRC" "$DEST"
echo "vendor 已安装到 $DEST"
