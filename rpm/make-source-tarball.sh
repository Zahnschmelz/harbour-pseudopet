#!/bin/bash
# make-source-tarball.sh — baut pseudopet-0.85-src.tar.gz für den RPM-Build [SFOS-PORT]
# Das Archiv enthält die Layout-Struktur, die pseudopet.spec erwartet:
#   pseudopet-0.85/src/  desktop/  systemd/  icons/
set -e
cd "$(dirname "$0")/.."
PROJ=$(pwd)
OUT="$PROJ/rpm"
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/pseudopet-0.85"
cp -a "$PROJ/src"     "$STAGE/pseudopet-0.85/"
cp -a "$PROJ/desktop" "$STAGE/pseudopet-0.85/"
cp -a "$PROJ/systemd" "$STAGE/pseudopet-0.85/"
cp -a "$PROJ/icons"   "$STAGE/pseudopet-0.85/"
# pycache raus
find "$STAGE" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || :

mkdir -p "$OUT"
tar -czf "$OUT/pseudopet-0.85-src.tar.gz" -C "$STAGE" pseudopet-0.85
echo "Erstellt: $OUT/pseudopet-0.85-src.tar.gz"
tar -tzf "$OUT/pseudopet-0.85-src.tar.gz" | head -8
