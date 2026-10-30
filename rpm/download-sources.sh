#!/bin/bash
# download-sources.sh — lädt alle Build-Quellen für pseudopet.spec [SFOS-PORT]
# Ausführen im Projektverzeichnis vor dem ersten Build (rpm/ muss existieren).
set -e
cd "$(dirname "$0")"

# SDL2, SDL2_ttf, SDL2_mixer und SDL2_image werden nicht mehr geladen: das
# Paket nutzt die Sailfish-eigenen SDL2-Pakete (BuildRequires: SDL2-devel,
# SDL2_ttf-devel, SDL2_mixer-devel, SDL2_image-devel).
DL=(
  "https://files.pythonhosted.org/packages/source/p/pygame/pygame-2.6.0.tar.gz|pygame-2.6.0.tar.gz"
  "https://files.pythonhosted.org/packages/source/w/websockets/websockets-12.0.tar.gz|websockets-12.0.tar.gz"
)

for entry in "${DL[@]}"; do
  url="${entry%%|*}"; fn="${entry##*|}"
  if [ -f "$fn" ]; then
    echo "vorhanden: $fn"
  else
    echo "lade: $fn"
    curl -L --fail -o "$fn" "$url"
  fi
done

echo "Alle Quellen bereit (rpm/)."
