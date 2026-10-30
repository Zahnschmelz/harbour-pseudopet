# Bauanleitung — PseudoPet für Sailfish OS

Spielbare Sailfish-OS-Portierung des Android-Retro-Tamagotchis **PseudoPet**
(240×320-Pixel-LCD-Look, Letterbox mit schwarzen Rändern wie im Android-
Original). Details zur Technik: `README_SAILFISH.md`.

## Voraussetzungen (Bau-PC, Linux x86-64)

- `sfdk` mit installiertem SDK-Ziel **`SailfishOS-5.1.0.11EA-aarch64`**
  (`sfdk config target=SailfishOS-5.1.0.11EA-aarch64`), sfdk im `PATH`
- Die Abhängigkeits-Quellen liegen bereits im Ordner `rpm/`
  (SDL2, SDL2_mixer, SDL2_ttf, freetype, pygame — für den Offline-Bau)
- Phone zum Testen: SFOS ≥ 5.x, aarch64, SSH freigeschaltet

## RPM bauen

Alles in **einem** Shell-Aufruf, aus der Projektwurzel:

```bash
export PATH=/pfad/zu/sfdk/bin:$PATH
bash rpm/make-source-tarball.sh          # erzeugt pseudopet-0.85-src.tar.gz
cp rpm/pseudopet.spec .sfdk/spec         # Spec pinnt auf %{_builddir}/pseudopet-%{version}
sfdk config target=SailfishOS-5.1.0.11EA-aarch64
sfdk build --prepare -j8
```

Ergebnis: `RPMS/harbour-pseudopet-0.85-1.aarch64.rpm`.

Wichtig: Das RPM installiert **aus dem Source0-Tarball**, nicht aus `src/`
direkt. Nach jeder Quelländerung deshalb zuerst
`bash rpm/make-source-tarball.sh` neu laufen lassen.

## Auf dem Phone installieren

```bash
scp -o UserKnownHostsFile=~/.ssh/known_hosts -i ~/.ssh/deploy_key \
    RPMS/harbour-pseudopet-0.85-1.aarch64.rpm defaultuser@PHONE:/tmp/
ssh defaultuser@PHONE        # dann als root:
rpm -Uvh --replacepkgs --nodeps /tmp/harbour-pseudopet-0.85-1.aarch64.rpm
```

Start über das App-Gitter (Icon „PseudoPet“) oder Manuell:

```bash
su - defaultuser -c 'export PYTHONUNBUFFERED=1 XDG_RUNTIME_DIR=/run/display \
  WAYLAND_DISPLAY=wayland-0 PULSE_SERVER=unix:/run/user/100000/pulse/native \
  DISPLAY=:0 XDG_SESSION_TYPE=wayland; \
  nohup /usr/bin/harbour-pseudopet > /tmp/pp-run.log 2>&1 &'
```

## Schneller In-Place-Deploy (nur Quell-Iteration, ohne RPM)

```bash
scp src/main.py defaultuser@PHONE:/tmp/
# als root auf dem Phone:
cp /tmp/main.py /usr/share/harbour-pseudopet/src/
rm -rf /usr/share/harbour-pseudopet/src/__pycache__
# neu starten (Muster gesplittet, damit pkill -f nicht auf sich selbst matcht):
PAT='harbour-pseudo'pet/src/main[.]py; pkill -f "$PAT"
# danach Neustart wie oben
```

Die Desktop-Datei (`desktop/org.beezi.harbour-pseudopet.desktop`) bewusst
nicht ändern: `X-Nemo-Application-Type=no-invoker`, `Sandboxing=Disabled`,
nackte `Exec=harbour-pseudopet`-Zeile (sonst „is not elf binary“).

## Headless-Tests (Bau-PC)

```bash
cd src
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m py_compile *.py
```

Positions-/Layout-Verifikation wie in `tests/` bzw. den Kopfer-Notizen von
`README_SAILFISH.md`: Canvas 240×528, `BAND_Y = 104`, alles Zeichnen auf
das Designfenster (240×320) beschnitten; `rh()/rhf()` sind **Positionen**,
Größen/Ampeliten immer kahl (bzw. `rs`) — sonst wandern Elemente um
+104 px nach unten (Schmetterling-/Defense-Bug-Historie).

## Screenshot vom Phone (Diagnose)

Lipstick verlangt vom aufrufenden Prozess die effektive GID der Gruppe
`privileged` (995). Als root auf dem Phone:

```bash
python3 -c "import os; os.setgroups([995,100000]); os.setgid(995); os.setuid(100000); \
os.environ['DBUS_SESSION_BUS_ADDRESS']='unix:path=/run/user/100000/dbus/user_bus_socket'; \
os.execvp('dbus-send',['dbus-send','--session','--print-reply', \
'--dest=org.nemomobile.lipstick','/org/nemomobile/lipstick/screenshot', \
'org.nemomobile.lipstick.saveScreenshot','string:/home/defaultuser/pp-shot.png'])"
```

Danach `scp defaultuser@PHONE:/home/defaultuser/pp-shot.png .`

## Git-Repo

Neues Repo ist initialisiert (`main`-Branch). Remote anlegen und pushen:

```bash
git remote add origin URL
git push -u origin main
```
