# PseudoPet for Sailfish OS 🐾 — Technical Documentation of the Sailfish OS Port

*Retro Tamagotchi port for the Jolla Phone (and other Sailfish OS 5.x devices)*

**Eat. Sleep. Evolve!** — Port of the original Python/Pygame game
(<https://github.com/Zahnschmelz/pseudoPet>) packaged as an RPM for
Sailfish OS, including edge-to-edge full screen on tall displays and
background notifications via systemd.

Tested on **Sailfish OS 5.2.0.22 „Finlayson" (aarch64)**, panel
1032×2272; package version `harbour-pseudopet-0.85-1.aarch64`.

---

## What this port does

| Area | Implementation |
|---|---|
| **Engine** | pygame 2.6 (built into the RPM) running on the **system SDL2** (SDL2 2.30 / SDL2_ttf / SDL2_mixer from `/usr/lib64`) — no SDL2 bundle, installed package size ~9.7 MB |
| **Full screen** | The 240×320 design sits pixel-accurate and centered in a canvas of **240×528** (the panel's aspect ratio) → edge-to-edge, square pixels |
| **Touch** | SDL2 Wayland client; A/B/C are handled like mouse buttons (menus, letter grid, all mini-games); the drawn buttons and the touch zones come from **the same layout function** |
| **Notifications** | D-Bus (`org.freedesktop.Notifications`) instead of the Android notification API |
| **Background alarms** | `systemd --user` timer (5 min) starts `keeper.py` — reads the save game, simulates the elapsed time using the **original game math** and reports: hatching, evolution, risk of death, hunger, sickness, poop, sadness |
| **Multiplayer Pong** | websockets 12.0 (pure Python, installed into `/usr/share/harbour-pseudopet/pylib`) — LAN host/join as in the original |
| **Save game** | `~/.local/share/pseudopet/pseudopet_save.json` (the app writes every 5 s, the keeper reads it) |
| **German/English** | automatic language detection as in the original |

## Project structure

```
pseudopet-sailfish/
├── src/                      Game code (patched; port changes marked with [SFOS-PORT])
│   ├── main.py               Game logic + full-screen/layout patches
│   ├── screen.py             Canvas-/band management (core of the full screen)
│   ├── sfdnotify.py          Dependency-free D-Bus notifications
│   ├── keeper.py             Background guardian (replacement for PetAlarmReceiver.java)
│   └── ...                   Further original modules + sounds + sprites
├── desktop/                  org.beezi.harbour-pseudopet.desktop + launcher /usr/bin/harbour-pseudopet
├── rpm/
│   ├── pseudopet.spec        RPM spec (package name: harbour-pseudopet)
│   ├── make-source-tarball.sh builds pseudopet-0.85-src.tar.gz (src/ desktop/ systemd/ icons/)
│   └── *.tar.gz              pygame-2.6.0.tar.gz, websockets-12.0.tar.gz (sources)
├── systemd/                  pseudopet-keeper.{service,timer}
├── icons/                    org.beezi.pseudopet.png (86/108/128)
└── screenshots/              Render verification
```

Installation layout on the device:

```
/usr/bin/harbour-pseudopet                    Launcher (shell script, sets the environment variables)
/usr/share/harbour-pseudopet/src/             Game code
/usr/share/harbour-pseudopet/pylib/           pygame 2.6 + websockets
/usr/share/applications/org.beezi.harbour-pseudopet.desktop
/usr/lib/systemd/user/pseudopet-keeper.{service,timer}
```

## Building with the Sailfish SDK

```bash
cd pseudopet-sailfish

# 1. Rebuild the source tarball (before EVERY build: the spec installs
#    FROM the tarball, not from src/)
bash rpm/make-source-tarball.sh

# 2. Setting the target and building must be in the SAME shell invocation,
#    the sfdk configuration is per-session:
export PATH=~/SailfishOS/bin:$PATH
cp rpm/pseudopet.spec .sfdk/spec
sfdk config target=SailfishOS-5.1.0.11EA-aarch64     # Check the name with `sfdk targets`
sfdk build --prepare -j8

# Result: RPMS/harbour-pseudopet-0.85-1.aarch64.rpm
```

Important spec details (also commented there):

- **Build tree = top-level directory of the tarball** (`pseudopet-%{version}`), not
  `%{name}-%{version}`: after the rename to `harbour-pseudopet`, the path
  pointed at a tree with the old name, the existence check
  `[ -d "$B/src" ]` succeeded, unpacking was skipped, and the install
  section copied **stale** files (launcher, desktop file, `main.py`) from
  the persistent sandbox build — the payloads stayed permanently out of
  date. Therefore: always unpack freshly and hard-code the tarball
  directory in `%prep`, `%build` and the install section.
- `pygame` is built against the system SDL2
  (`SDL_CONFIG=/usr/bin/sdl2-config`); the optional extensions
  `_sdl2`, `pypm`, `_sprite`, `_freetype` are removed from the generated
  `Setup` file, and `freesansbold.ttf` and `pygame_icon.bmp` are
  explicitly copied into the package tree.
- `python3dist(curses)` (an automatic dependency of pygame) cannot be
  resolved on Sailfish → use `--nodeps` when installing.

## Installation on the device

```bash
scp harbour-pseudopet-0.85-1.aarch64.rpm defaultuser@<device-ip>:/tmp/
ssh defaultuser@<device-ip>
devel-su rpm -Uvh --replacepkgs --nodeps /tmp/harbour-pseudopet-0.85-1.aarch64.rpm
```

Then enable the **keeper timer** once (background alarms):

```bash
systemctl --user enable --now pseudopet-keeper.timer
```

The app appears in the app grid as **PseudoPet**.

## Two Sailfish specifics you need to know

1. **Desktop file: application type and sandboxing.** The launcher is a
   shell script. `X-Nemo-Application-Type=silica-qt5` (and any unknown or
   legacy value as a fallback) starts Invoker + mapplauncherd booster +
   Sailjail, and those require an ELF binary — startup aborts with
   `harbour-pseudopet: is not elf binary: Inappropriate ioctl for device`.
   Exactly these entries are required:

   ```ini
   X-Nemo-Application-Type=no-invoker
   Exec=harbour-pseudopet

   [X-Sailjail]
   Sandboxing=Disabled
   ```

   `Sandboxing=Disabled` is mandatory: Sailfish OS enforces the sandbox for
   every package whose program name starts with `harbour-`
   (`warning: enforcing sandboxing for '/usr/bin/harbour-pseudopet'`) —
   inside the sandbox the launcher cannot reach the Wayland socket
   `/run/display/wayland-0` nor the PulseAudio sockets.

2. **Mali/libhybris needs `EGL_PLATFORM=wayland`.** Without this variable
   `/usr/lib64/libEGL.so.1` selects the Android platform module, and pygame
   dies on the first window with
   `egl.c:344: eglCreateWindowSurface: Assertion '… ANDROID_NATIVE_WINDOW_MAGIC' failed`
   (SIGABRT). The launcher `/usr/bin/harbour-pseudopet` sets the variable
   in an overridable way: `EGL_PLATFORM="${EGL_PLATFORM:-wayland}"`.

## Full screen on tall panels

Lipstick/Weston scales every surface while preserving its aspect ratio and
aligns it to the top. A window with a 3:4 ratio (480×640) becomes
1032×1376 on the 1032×2272 panel: as a result, the game world and the
A/B/C buttons ended "in the middle of the screen", and the touch zones lay
below it in the black area. The port therefore creates the full-screen
window in the proportions of the panel — `_panel_size()` reads
`/sys/class/drm/card*-*/modes` (overridable with `PSEUDOPET_PANEL=WxH`;
`pygame.display.Info()` only reports the window size on Wayland, not the
display's). From this the canvas `240×528` is derived (`screen.py`): the
design window (240×320) sits centered in it with `BAND_Y = 104`,
**black remains above and below it** — exactly the letterbox look of the
Android template. `draw()` clips all drawing operations to the band
(`set_clip`), `_fill_bg()` paints the border black, and world particles
(rain, snow, shooting stars) draw in design coordinates one band level
lower. `_init_layout()` places the A/B/C areas as **flat ellipses
(66×30)** at the design position y = 282..312 — 8 px above the bottom edge
of the band, as in the Android original. The same values feed
`_button_zones()` (touch zones extending to the bottom edge of the
canvas), so drawing and tapping always hit the same area.

## Controls

Identical to the original: three touch zones at the very bottom
(A | B | C), corresponding to the Android buttons. Holding A/C repeats
(e.g. scrolling the letter grid). The fishing mini-game also needs
holding ("HOLD B = raise the catch window"): because Wayland touch does
not populate the polled mouse/keyboard state (`pygame.*.get_pressed()`),
`fishing.py` reads the hold state from the main loop's touch tracking
(`mouse_down` + `mouse_hold_btn`) — the same mechanism that drives the
repeating in the letter grid.

## Background guardian in detail

- While the app is running, **the keeper stays silent** (the app writes a
  heartbeat to `~/.local/share/pseudopet/.heartbeat` every 5 s and sends
  notifications itself).
- When the app is closed, the keeper checks every 5 minutes:
  - **Hatching/evolution** — up to 6 min in advance (bypasses quiet hours,
    as in the original)
  - **Risk of death** — 30-minute projection using the same simulation logic
  - **Hunger / sickness / ≥ 3 droppings / sadness** — with quiet hours
    (23:00–06:00) and a 5-minute cooldown per category
- Settings in the game (notifications on/off) also apply to the keeper.
- Status: `systemctl --user list-timers | grep pseudopet`;
  logs: `journalctl --user -u pseudopet-keeper.service`
- Disable: `systemctl --user disable --now pseudopet-keeper.timer`

## Diagnostics

| Problem | Solution |
|---|---|
| Tapping the icon does nothing, journal shows `is not elf binary` | Desktop file as above: `X-Nemo-Application-Type=no-invoker` + `[X-Sailjail] Sandboxing=Disabled`; reinstall the package after changing it |
| `enforcing sandboxing for '/usr/bin/harbour-pseudopet'` + abort | `Sandboxing=Disabled` is missing (mandatory for `harbour-` packages) |
| Crash with the `ANDROID_NATIVE_WINDOW_MAGIC` assertion | `EGL_PLATFORM=wayland` (the launcher sets it; test: `EGL_PLATFORM=wayland /usr/bin/harbour-pseudopet`) |
| No sound | The launcher looks for the PulseAudio socket in `$XDG_RUNTIME_DIR` and `/run/user/100000`; check `pactl info` — the game also runs in silence |
| Display not completely filled | `cat /sys/class/drm/card0-DSI-1/modes`; help it along with `PSEUDOPET_PANEL=WxH` |
| Classic behavior wanted | `PSEUDOPET_FILL=0` (only 240×320), `PSEUDOPET_SCALE=int` (pixel-accurate integer scaling with bars) |
| Too dark/bright | Original feature: `--day` / `--night` as startup parameters |
| RPM installation fails on `python3dist(curses)` | `rpm -ivh --nodeps …` (pygame does not need curses; the package is named differently on Sailfish) |
| Changes in `src/` do not show up in the RPM | Rebuild the tarball with `bash rpm/make-source-tarball.sh`; the spec now always unpacks freshly |

## Technical notes on the port

1. **Canvas design**: `screen.py` manages `VW/VH/BAND_Y`. Positions (`rh`)
   are shifted by the band offset, sizes/distances (`rs`) stay true to the
   design; on the desktop (BAND_Y = 0) everything behaves as in the
   original.
2. **Layout from a single source**: `_init_layout()` sets `_btn_top` and
   `self.buttons`, `_button_zones()` derives the touch zones from that.
   Previously the hard-coded Android values (x = 25/92/159, y = 285,
   55×28) in `__init__` overwrote the layout after `apply_resolution()`
   had computed it — the buttons were drawn in the middle of the floor,
   the touch zones lay at the bottom.
3. **No shared state**: the keeper never writes the save game; it
   reconstructs the pet with `Pet.from_dict` and simulates with
   `Pet.simulate_offline` — the same code the app uses when reopening.
4. **No plyer/pyjnius/kivy**: the Android imports are only active on
   Android (`platform() == "android"`); Sailfish runs through the
   `sailfish` branch (detected via `/etc/sailfish-release`).
5. **Upstream-compatible**: all port changes are commented with
   `[SFOS-PORT]` and can be carried over to a new upstream release.

## License

As in the original: **MIT** (see `src/LICENSE`).
Sound credits: see the upstream README (CC0/Pixabay/CC BY 4.0).
