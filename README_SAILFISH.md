# PseudoPet für Sailfish OS 🐾

*Retro-Tamagotchi-Port für das Jolla Phone (und andere Sailfish-OS-5.x-Geräte)*

**Eat. Sleep. Evolve!** — Port des Python/Pygame-Originals
(<https://github.com/Zahnschmelz/pseudoPet>) als RPM-Paketierung für
Sailfish OS, inklusive randvollem Vollbild auf langen Displays und
Hintergrund-Benachrichtigungen über systemd.

Getestet auf **Sailfish OS 5.2.0.22 „Finlayson“ (aarch64)**, Panel
1032×2272; Paketstand `harbour-pseudopet-0.85-1.aarch64`.

---

## Was dieser Port macht

| Bereich | Umsetzung |
|---|---|
| **Engine** | pygame 2.6 (in das RPM eingebaut) läuft auf dem **SDL2 des Systems** (SDL2 2.30 / SDL2_ttf / SDL2_mixer aus `/usr/lib64`) — kein SDL2-Bundle, installierte Paketgröße ~9,7 MB |
| **Vollbild** | 240×320-Design sitzt pixelgetreu zentriert in einem Canvas von **240×528** (Seitenverhältnis des Panels) → randvoll, quadratische Pixel |
| **Touch** | SDL2-Wayland-Client; A/B/C werden wie Maustasten verarbeitet (Menüs, Buchstabengitter, alle Mini-Games); gezeichnete Buttons und Touch-Zonen kommen aus **derselben Layout-Funktion** |
| **Benachrichtigungen** | D-Bus (`org.freedesktop.Notifications`) statt Android-Notification-API |
| **Hintergrund-Alarme** | `systemd --user`-Timer (5 min) startet `keeper.py` — liest den Spielstand, simuliert die vergangene Zeit mit der **Original-Spielmathematik** und meldet: Schlüpfen, Evolution, Todesgefahr, Hunger, Krankheit, Kacka, Traurigkeit |
| **Multiplayer-Pong** | Websockets 12.0 (pure Python, nach `/usr/share/harbour-pseudopet/pylib` eingebaut) — LAN-Host/Join wie im Original |
| **Spielstand** | `~/.local/share/pseudopet/pseudopet_save.json` (App schreibt alle 5 s, Keeper liest) |
| **Deutsch/Englisch** | automatische Spracherkennung wie im Original |

## Projektstruktur

```
pseudopet-sailfish/
├── src/                      Spielcode (gepatcht, Port-Stellen mit [SFOS-PORT] markiert)
│   ├── main.py               Spiellogik + Vollbild-/Layout-Patches
│   ├── screen.py             Canvas-/Band-Verwaltung (Vollbild-Kern)
│   ├── sfdnotify.py          D-Bus-Benachrichtigungen ohne Abhängigkeiten
│   ├── keeper.py             Hintergrund-Wächter (Ersatz für PetAlarmReceiver.java)
│   └── ...                   weitere Original-Module + Sounds + Sprites
├── desktop/                  org.beezi.harbour-pseudopet.desktop + Starter /usr/bin/harbour-pseudopet
├── rpm/
│   ├── pseudopet.spec        RPM-Spec (Paketname: harbour-pseudopet)
│   ├── make-source-tarball.sh baut pseudopet-0.85-src.tar.gz (src/ desktop/ systemd/ icons/)
│   └── *.tar.gz              pygame-2.6.0.tar.gz, websockets-12.0.tar.gz (Quellen)
├── systemd/                  pseudopet-keeper.{service,timer}
├── icons/                    org.beezi.pseudopet.png (86/108/128)
└── screenshots/              Render-Verifikation
```

Installationslayout auf dem Gerät:

```
/usr/bin/harbour-pseudopet                    Starter (Shellskript, setzt die Umgebungsvariablen)
/usr/share/harbour-pseudopet/src/             Spielcode
/usr/share/harbour-pseudopet/pylib/           pygame 2.6 + websockets
/usr/share/applications/org.beezi.harbour-pseudopet.desktop
/usr/lib/systemd/user/pseudopet-keeper.{service,timer}
```

## Build mit dem Sailfish SDK

```bash
cd pseudopet-sailfish

# 1. Quell-Tarball neu bauen (vor JEDEM Build: die Spec installiert
#    AUS dem Tarball, nicht aus src/)
bash rpm/make-source-tarball.sh

# 2. Target-Setzen und Bauen müssen im SELBEN Shell-Aufruf stehen,
#    die sfdk-Konfiguration ist sitzungsbezogen:
export PATH=~/SailfishOS/bin:$PATH
cp rpm/pseudopet.spec .sfdk/spec
sfdk config target=SailfishOS-5.1.0.11EA-aarch64     # Name per `sfdk targets` prüfen
sfdk build --prepare -j8

# Ergebnis: RPMS/harbour-pseudopet-0.85-1.aarch64.rpm
```

Wichtige Spec-Details (dort auch kommentiert):

- **Build-Baum = Top-Ordner des Tarballs** (`pseudopet-%{version}`), nicht
  `%{name}-%{version}`: nach der Umbenennung in `harbour-pseudopet` zeigte
  der Pfad auf einen Baum des alten Namens, die Existenzprüfung
  `[ -d "$B/src" ]` traf zu, das Entpacken wurde übersprungen, und der
  Installationsabschnitt kopierte **alte** Dateien (Starter, Desktop-Datei,
  `main.py`) aus dem persistenten Sandbox-Bau — die Payloads blieben
  dauerhaft veraltet. Deshalb: immer neu entpacken und den Tarball-Ordner
  in `%prep`, `%build` und im Installationsabschnitt fest verankern.
- `pygame` wird gegen das SDL2 des Systems gebaut
  (`SDL_CONFIG=/usr/bin/sdl2-config`); die optionalen Erweiterungen
  `_sdl2`, `pypm`, `_sprite`, `_freetype` werden aus der generierten
  `Setup`-Datei entfernt, `freesansbold.ttf` und `pygame_icon.bmp` werden
  explizit in den Paketbaum kopiert.
- `python3dist(curses)` (Autoabhängigkeit von pygame) ist auf Sailfish
  nicht auflösbar → bei der Installation `--nodeps` verwenden.

## Installation auf dem Gerät

```bash
scp harbour-pseudopet-0.85-1.aarch64.rpm defaultuser@<gerät-ip>:/tmp/
ssh defaultuser@<gerät-ip>
devel-su rpm -Uvh --replacepkgs --nodeps /tmp/harbour-pseudopet-0.85-1.aarch64.rpm
```

Anschließend einmalig den **Keeper-Timer** aktivieren (Hintergrund-Alarme):

```bash
systemctl --user enable --now pseudopet-keeper.timer
```

Die App erscheint im App-Raster als **PseudoPet**.

## Zwei Sailfish-Besonderheiten, die man kennen muss

1. **Desktop-Datei: App-Typ und Sandboxing.** Der Starter ist ein
   Shellskript. `X-Nemo-Application-Type=silica-qt5` (und jeder unbekannte
   bzw. Legacy-Wert als Fallback) startet Invoker + mapplauncherd-Booster +
   Sailjail, und die verlangen eine ELF-Datei — der Start bricht ab mit
   `harbour-pseudopet: is not elf binary: Inappropriate ioctl for device`.
   Nötig sind genau diese Einträge:

   ```ini
   X-Nemo-Application-Type=no-invoker
   Exec=harbour-pseudopet

   [X-Sailjail]
   Sandboxing=Disabled
   ```

   `Sandboxing=Disabled` ist Pflicht: Sailfish OS erzwingt die Sandbox für
   jedes Paket, dessen Programmname mit `harbour-` beginnt
   (`warning: enforcing sandboxing for '/usr/bin/harbour-pseudopet'`) — in
   der Sandbox kommt der Starter nicht an die Wayland-Socket
   `/run/display/wayland-0` und nicht an die PulseAudio-Sockets.

2. **Mali/libhybris braucht `EGL_PLATFORM=wayland`.** Ohne diese Variable
   wählt `/usr/lib64/libEGL.so.1` das Android-Plattformmodul, und pygame
   stirbt beim ersten Fenster mit
   `egl.c:344: eglCreateWindowSurface: Assertion '… ANDROID_NATIVE_WINDOW_MAGIC' failed`
   (SIGABRT). Der Starter `/usr/bin/harbour-pseudopet` setzt die Variable
   überschreibbar: `EGL_PLATFORM="${EGL_PLATFORM:-wayland}"`.

## Vollbild auf langen Panels

Lipstick/Weston skaliert jede Fensterfläche unter Beibehaltung des
Seitenverhältnisses und richtet sie oben aus. Ein Fenster im Verhältnis
3:4 (480×640) wird auf dem 1032×2272-Panel zu 1032×1376: Spielwelt und
A/B/C-Buttons endeten dadurch „mitten im Bild“, die Touch-Zonen lagen
darunter im Schwarzen. Der Port legt das Vollbild-Fenster deshalb in den
Proportionen des Panels an — `_panel_size()` liest
`/sys/class/drm/card*-*/modes` (überschreibbar mit `PSEUDOPET_PANEL=WxH`;
`pygame.display.Info()` liefert auf Wayland nur die Fenstergröße, nicht
die des Displays). Daraus entsteht das Canvas `240×528` (`screen.py`):
Das Designfenster (240×320) sitzt mit `BAND_Y = 104` zentriert darin,
**darüber und darunter bleibt Schwarz** — exakt der Letterbox-Look der
Android-Vorlage. `draw()` beschneidet sämtliche Zeichenoperationen auf
das Band (`set_clip`), `_fill_bg()` malt den Rand schwarz, und
Welt-Partikel (Regen, Schnee, Sternschnuppen) zeichnen in
Designkoordinaten eine Band-Etage tiefer. `_init_layout()` setzt die
A/B/C-Flächen als **flache Ellipsen (66×30)** auf die Design-Position
y = 282..312 — 8 px über der Bandunterkante, wie im Android-Original.
Dieselben Rechte leiten `_button_zones()` ab (Touch-Zonen bis an die
Canvas-Unterkante), also trifft Zeichnen und Tippen immer dieselbe
Fläche.

## Bedienung

Identisch zum Original: drei Touch-Zonen ganz unten (A | B | C),
entsprechen den Android-Tasten. Halten von A/C wiederholt (z. B.
Buchstabengitter scrollen). Auch das Angelspiel braucht Halten
(„B HALTEN = Fangfenster heben“): Da Wayland-Touch den gepollten
Maus-/Tastaturstatus (`pygame.*.get_pressed()`) nicht fuellt, liest
`fishing.py` den Halte-Zustand aus der Touch-Verfolgung der
Hauptschleife (`mouse_down` + `mouse_hold_btn`) — derselbe Mechanismus,
der das Wiederholen im Buchstabengitter antreibt.

## Hintergrund-Wächter im Detail

- Läuft die App, **schweigt der Keeper** (App schreibt alle 5 s einen
  Heartbeat nach `~/.local/share/pseudopet/.heartbeat` und benachrichtigt selbst).
- Ist die App geschlossen, prüft der Keeper alle 5 Minuten:
  - **Schlüpfen/Evolution** — bis zu 6 min im Voraus (umgeht Ruhezeit, wie im Original)
  - **Todesgefahr** — 30-Minuten-Projektion mit derselben Simulationslogik
  - **Hunger / Krankheit / ≥ 3 Häufchen / Traurigkeit** — mit Ruhezeit
    (23:00–06:00) und 5-Minuten-Cooldown pro Kategorie
- Einstellungen (Notifications an/aus) im Spiel gelten auch für den Keeper.
- Status: `systemctl --user list-timers | grep pseudopet`;
  Logs: `journalctl --user -u pseudopet-keeper.service`
- Deaktivieren: `systemctl --user disable --now pseudopet-keeper.timer`

## Diagnose

| Problem | Lösung |
|---|---|
| Icon-Start macht nichts, im Journal steht `is not elf binary` | Desktop-Datei wie oben: `X-Nemo-Application-Type=no-invoker` + `[X-Sailjail] Sandboxing=Disabled`; nach dem Ändern Paket neu installieren |
| `enforcing sandboxing for '/usr/bin/harbour-pseudopet'` + Abbruch | `Sandboxing=Disabled` fehlt (Pflicht für `harbour-`-Pakete) |
| Absturz mit `ANDROID_NATIVE_WINDOW_MAGIC`-Assertion | `EGL_PLATFORM=wayland` (Starter setzt sie; Test: `EGL_PLATFORM=wayland /usr/bin/harbour-pseudopet`) |
| Kein Ton | Starter sucht die PulseAudio-Socket in `$XDG_RUNTIME_DIR` und `/run/user/100000`; `pactl info` prüfen — das Spiel läuft auch stumm |
| Display wird nicht ganz gefüllt | `cat /sys/class/drm/card0-DSI-1/modes`; mit `PSEUDOPET_PANEL=WxH` nachhelfen |
| Klassisches Verhalten gewünscht | `PSEUDOPET_FILL=0` (nur 240×320), `PSEUDOPET_SCALE=int` (pixelgenaue Ganzzahl-Skalierung mit Balken) |
| Zu dunkel/hell | Original-Feature: `--day` / `--night` als Startparameter |
| RPM-Installation scheitert an `python3dist(curses)` | `rpm -ivh --nodeps …` (pygame braucht curses nicht, das Paket heißt auf Sailfish anders) |
| Änderungen an `src/` tauchen im RPM nicht auf | Tarball mit `bash rpm/make-source-tarball.sh` neu bauen; Spec entpackt jetzt immer frisch |

## Technische Anmerkungen zum Port

1. **Canvas-Design**: `screen.py` verwaltet `VW/VH/BAND_Y`. Positionen
   (`rh`) verschieben sich um den Band-Offset, Größen/Distanzen (`rs`)
   bleiben designgetreu; auf dem Desktop (BAND_Y = 0) ist alles wie im
   Original.
2. **Layout aus einer Hand**: `_init_layout()` setzt `_btn_top` und
   `self.buttons`, `_button_zones()` leitet die Touch-Zonen daraus ab.
   Zuvor überschrieben die harten Android-Rechte (x = 25/92/159, y = 285,
   55×28) in `__init__` das Layout, nachdem `apply_resolution()` es
   berechnet hatte — die Buttons wurden mitten auf den Fußboden gezeichnet,
   die Touch-Zonen lagen unten.
3. **Keine geteilten Zustände**: Der Keeper schreibt nie den Spielstand;
   er rekonstruiert das Pet per `Pet.from_dict` und simuliert mit
   `Pet.simulate_offline` — derselbe Code, den die App beim Wiederöffnen
   nutzt.
4. **Kein plyer/pyjnius/kivy**: Android-Importe sind nur auf Android aktiv
   (`platform() == "android"`); Sailfish läuft über den `sailfish`-Zweig
   (Erkennung über `/etc/sailfish-release`).
5. **Upstream-kompatibel**: Alle Port-Stellen sind mit `[SFOS-PORT]`
   kommentiert und lassen sich auf ein neues Upstream-Release übernehmen.

## Lizenz

Wie das Original: **MIT** (siehe `src/LICENSE`).
Sound-Credits siehe Upstream-README (CC0/Pixabay/CC BY 4.0).
