#
# pseudopet.spec — Sailfish OS RPM [SFOS-PORT]
#
# Retro-Tamagotchi (Python/Pygame) für Sailfish OS 5.x (aarch64),
# z. B. Jolla Phone 2026.
#
# Strategie: SDL2, SDL2_ttf, SDL2_mixer, SDL2_image und Python 3.11 sind auf
# dem Gerät als Sailfish-eigene Pakete vorhanden (SDL2 2.30.10 mit
# Wayland-Treiber; auf dem Telefon läuft kein X11/Xwayland). Es wird nichts
# mitgebündelt, sondern gegen die Systembibliotheken gebaut: das Paket bleibt
# klein, und es läuft genau das SDL2, das für Sailfish gebaut wurde.
#
# pygame 2.6.0 wird aus dem Quelltext gebaut (im SFOS-Repo gibt es kein
# python3-pygame). PseudoPet braucht pygame._sdl2, pypm (PortMidi), _sprite
# und pygame.freetype nicht; diese Module werden in der pygame-Konfiguration
# abgestellt, damit der Build deterministisch bleibt.
#
# Quellen zuerst laden:  bash rpm/download-sources.sh
# Bauen:                 sfdk build --prepare
# (ohne --prepare wird die obige Prep-Sektion von sfdk übersprungen; der
#  Build-Block entpackt das Quellarchiv deshalb zusätzlich selbst)
#

# Der Python-Abhaengigkeitsgenerator meldet python3dist(curses) (in pygame
# wird curses nur in Beispiel- und Testdateien der pygame-Distribution
# benutzt, die nicht mitkommen). curses ist ein Teil der Python-
# Standardbibliothek; auf dem Telefon gibt es dafuer kein eigenes Paket,
# deshalb wird genau dieser automatische Eintrag unterdrtueckt.
%define __requires_exclude ^python3dist\(curses\)$

# Kein -debuginfo-Unterpaket: das Paket enthält Python- und Spieldaten, ein
# Rumpf-paket ohne debuginfo-Anteil würde als "unpackaged files" scheitern.
%define debug_package %{nil}

Name:           harbour-pseudopet
Version:        0.85
Release:        1
Summary:        PseudoPet — Retro-Tamagotchi for Sailfish OS
License:        MIT
URL:            https://github.com/Zahnschmelz/pseudoPet
Source0:        pseudopet-0.85-src.tar.gz
Source1:        pygame-2.6.0.tar.gz
Source2:        websockets-12.0.tar.gz

# Python-Laufzeit
BuildRequires:  python3-base
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
# SDL2-Stack des Systems (identische Versionen wie auf dem Gerät)
BuildRequires:  SDL2-devel
BuildRequires:  SDL2_ttf-devel
BuildRequires:  SDL2_mixer-devel
BuildRequires:  SDL2_image-devel
BuildRequires:  pkgconfig(zlib)
BuildRequires:  pkgconfig(libpng)
BuildRequires:  make
BuildRequires:  gcc
BuildRequires:  gcc-c++

# Laufzeit: SDL2-Stack und Python. Die zusätzlichen Skripte
# (zynk_pseudopet.py für die Handy-Integration, sfdnotify.py für
# Sailfish-Notifications) sind optional: python3-requests, python3-websockets
# und python3-dbus sind auf dem Gerät nicht installiert, die Skripte greifen
# auf dbus-send zurück bzw. werden nur bei Bedarf verwendet.
Requires:       SDL2
Requires:       SDL2_ttf
Requires:       SDL2_mixer
Requires:       python3-base
Requires:       python3-libs

%description
PseudoPet ist ein Tamagotchi-artiges Haustier, das in Python und pygame
geschrieben wurde und ohne Bildschirmtastatur auskommt: Die Steuerung über
die Pfeiltasten wurde durch einen virtuellen D-Pad-Overlay ersetzt, mit dem
sich das Spiel vollständig per Touch bedienen lässt.

Zusätzlich können die Bedürfnisse des Tiers über die Bluetooth-/HTTP-API des
Spiels aktualisiert werden (zynk_pseudopet.py), und Benachrichtigungen
erscheinen als Sailfish-Notification (sfdnotify.py, wahlweise über
python3-dbus oder über dbus-send). Für die Wartung von unten gibt es einen
Headless-Modus (keeper.py), der die Spielzustandsdatei aktualisiert, ohne
das Fenster zu öffnen.

%prep
# Das Quellarchiv hat den festen Top-Ordner "pseudopet-Version" (so erzeugt
# ihn make-source-tarball.sh). Der Paketname darf hier nicht verwendet
# werden: nach der Umbenennung in "harbour-pseudopet" zeigte der
# Build-Baum-Pfad auf einen Baum des alten Namens, die Existenzpruefung
# traf zu, das Entpacken wurde uebersprungen und der Installationsabschnitt
# kopierte die alten Dateien (Starter, Desktop-Datei, main.py) aus dem
# persistenten Sandbox-Bau. Deshalb wird der Top-Ordner hier explizit und
# immer frisch angelegt.
rm -rf "%{_builddir}/pseudopet-%{version}"
tar -xf %{SOURCE0} -C "%{_builddir}"

%build
B="%{_builddir}/pseudopet-%{version}"
[ -d "$B/src" ] || { rm -rf "$B"; tar -xf %{SOURCE0} -C "%{_builddir}"; }
mkdir -p "$B/_build"

# ---------------- 1) pygame 2.6.0 gegen das SDL2 des Systems -------------
rm -rf "$B/_build/pygame-2.6.0"
tar -xf %{SOURCE1} -C "$B/_build"
cd "$B/_build/pygame-2.6.0"

    # SDL2 aus dem System: sdl2-config gehört zu SDL2-devel.
    export SDL_CONFIG=/usr/bin/sdl2-config
    # SDL_ttf.h, SDL_image.h und SDL_mixer.h liegen in /usr/include/SDL2.
    # Diese Umgebungsvariablen wertet pygame/baseconfig aus; sie machen die
    # Konfiguration unabhängig von den Suchpfad-Räumen der Dep-Prüfung.
    export FONT_CFLAGS="-I/usr/include/SDL2"   FONT_LIBS="-lSDL2_ttf"
    export IMAGE_CFLAGS="-I/usr/include/SDL2"  IMAGE_LIBS="-lSDL2_image"
    export MIXER_CFLAGS="-I/usr/include/SDL2"  MIXER_LIBS="-lSDL2_mixer"
    export FREETYPE_CFLAGS="$(pkg-config --cflags freetype2)"
    export FREETYPE_LIBS="$(pkg-config --libs freetype2)"
    # Guerturame fuer die Compilertest *und* die eigentlichen Module:
    # SDL2-Header liegen in /usr/include/SDL2, die Bibliotheken in
    # /usr/lib64. distutils uebernimmt diese Variablen in die Compile-/
    # Link-Kommandos, damit -lSDL2_ttf, -lSDL2_mixer und -lSDL2_image
    # auch dann gefunden werden, wenn pygame die Bibliothekverzeichnisse
    # selbst nicht erkennt.
    export CFLAGS="$CFLAGS -I/usr/include/SDL2 -I/usr/include/freetype2"
    export LDFLAGS="$LDFLAGS -L/usr/lib64"

    # Cython-Gate: pygame 2.6 bricht ab, wenn die generierten C-Dateien
    # fehlen und kein Cython installiert ist. Die betroffenen Module werden
    # nicht gebraucht, deshalb Platzhalter anlegen und die Module aus der
    # Moduliste werfen.
    mkdir -p src_c/_sdl2
    : > src_c/_sdl2/audio.c
    : > src_c/pypm.c
    python3 -c "import buildconfig.config as c; c.main(True)"
    sed -i -e '/^_sdl2\./d' -e '/^pypm /d' -e '/^_sprite /d' \
           -e '/^_freetype /d' Setup
    echo "--- pygame: kompilierte Module ---"
    grep -E "^[A-Za-z_]+ " Setup | cut -d' ' -f1 | tr '\n' ' '
    echo
    python3 setup.py build --build-lib=pygame-build
    # Die Datendateien (Standardfont, Fenster-Icon) uebergibt der
    # Distutils-Bau nicht an das Build-Verzeichnis; sie liegen im Quell-
    # unterverzeichnis src_py und werden hier explicit hinterlegt. Ohne
    # freesansbold.ttf scheitert jeder Aufruf der Default-Font.
    cp -a src_py/freesansbold.ttf pygame-build/pygame/
    cp -a src_py/pygame_icon.bmp  pygame-build/pygame/
    mkdir -p "$B/pylib"
    cp -a pygame-build/pygame "$B/pylib/"
cd "$B"

# ---------------- 2) websockets (pure Python) ---------------------------
tar -xf %{SOURCE2} -C "$B/_build"
cd "$B"/_build/websockets-*
    mkdir -p "$B/pylib"
    cp -a src/websockets "$B/pylib/"
    find "$B/pylib/websockets" -name "*.pyc" -delete
cd "$B"

# Bytecode (optional, beschleunigt den Start)
python3 -m compileall -q "$B/pylib" || :

%install
B="%{_builddir}/pseudopet-%{version}"
mkdir -p %{buildroot}%{_datadir}/harbour-pseudopet/{src,pylib}
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/{86x86,108x108,128x128}/apps
mkdir -p %{buildroot}%{_prefix}/lib/systemd/user

cp -a "$B"/src/.        %{buildroot}%{_datadir}/harbour-pseudopet/src/
cp -a "$B"/pylib/.      %{buildroot}%{_datadir}/harbour-pseudopet/pylib/

# pygame-Beispiele, Selbsttests, Dokumentation und Themes werden nicht
# bentigt: das spart rund 3 MB auf dem Telefon.
rm -rf %{buildroot}%{_datadir}/harbour-pseudopet/pylib/pygame/tests \
       %{buildroot}%{_datadir}/harbour-pseudopet/pylib/pygame/examples \
       %{buildroot}%{_datadir}/harbour-pseudopet/pylib/pygame/docs \
       %{buildroot}%{_datadir}/harbour-pseudopet/pylib/pygame/themes
find %{buildroot}%{_datadir}/harbour-pseudopet/pylib -name "*.pyc" -delete

# Lizenz auf Paketebene ablegen, damit sie nicht innerhalb der Spieldaten
# ein zweites Mal aufgelistet wird.
install -m 644 "$B"/src/LICENSE %{buildroot}%{_datadir}/harbour-pseudopet/LICENSE
rm -f %{buildroot}%{_datadir}/harbour-pseudopet/src/LICENSE

install -m 755 "$B"/desktop/harbour-pseudopet.sh %{buildroot}%{_bindir}/harbour-pseudopet
install -m 644 "$B"/desktop/org.beezi.harbour-pseudopet.desktop \
    %{buildroot}%{_datadir}/applications/
for s in 86x86 108x108 128x128; do
    install -m 644 "$B"/icons/$s/org.beezi.pseudopet.png \
        %{buildroot}%{_datadir}/icons/hicolor/$s/apps/ 2>/dev/null || :
done
install -m 644 "$B"/systemd/pseudopet-keeper.service \
    "$B"/systemd/pseudopet-keeper.timer \
    %{buildroot}%{_prefix}/lib/systemd/user/

%files
# Die Pfade sind absichtlich absolut: weil das Quellarchiv im Build-Block
# selbst entpackt wird, ist das Quellverzeichnis nicht als Paket-
# Buildunterverzeichnis gesetzt, und relative Pfade wären nicht zuverlässig.
# Die Lizenzdatei liegt im Datenverzeichnis und ist damit abgedeckt.
%{_bindir}/harbour-pseudopet
%{_datadir}/applications/org.beezi.harbour-pseudopet.desktop
%{_datadir}/icons/hicolor/*/apps/org.beezi.pseudopet.png
%{_datadir}/harbour-pseudopet/
%{_prefix}/lib/systemd/user/pseudopet-keeper.service
%{_prefix}/lib/systemd/user/pseudopet-keeper.timer
