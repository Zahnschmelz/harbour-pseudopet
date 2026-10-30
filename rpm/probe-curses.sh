#!/bin/sh
# Einmalige Diagnose: Welche Datei im RPM-Payload erzeugt den automatischen
# Abhaengigkeits-Eintrag python3dist(curses)? Laeuft im sfdk-Baucontainer.
RPM="$1"
cd /tmp || exit 1
rm -rf probe && mkdir probe && cd probe || exit 1
rpm2cpio "$RPM" | cpio -idm --quiet

echo "--- Dateien, die beim Dep-Generator curses melden ---"
find . -type f | while read -r f; do
    out=$(/usr/lib/rpm/pythonappdeps.sh "$f" 2>/dev/null)
    case "$out" in
        *curses*) echo "DATEI: $f"
                  echo "  -> $out" ;;
    esac
done

echo "--- Regex-Selbsttest ---"
printf 'python3dist(curses)\n' | grep -qE '^python3dist\(curses\)$' && echo REGEX_OK || echo REGEX_FAIL

echo "--- Macro-Werte im Container ---"
echo "Standard: [$(rpm --eval '%{__requires_exclude}')]"
echo "Mit Define: [$(rpm --eval --define '__requires_exclude ^python3dist\(curses\)$' '%{__requires_exclude}')]"

echo "--- Dep-Generator fuer pygame/__init__.py ---"
/usr/lib/rpm/pythonappdeps.sh ./usr/share/pseudopet/pylib/pygame/__init__.py 2>&1 | head -20
