# Build Instructions — PseudoPet for Sailfish OS

Playable Sailfish OS port of the Android retro Tamagotchi **PseudoPet**
(240×320 pixel LCD look, letterboxed with black borders as in the Android
original). Technical details: `README_TECHNICAL.md`.

## Prerequisites (build PC, Linux x86-64)

- `sfdk` with the installed SDK target **`SailfishOS-5.1.0.11EA-aarch64`**
  (`sfdk config target=SailfishOS-5.1.0.11EA-aarch64`), sfdk in `PATH`
- The dependency sources are already in the `rpm/` folder
  (SDL2, SDL2_mixer, SDL2_ttf, freetype, pygame — for offline builds)
- A phone for testing: SFOS ≥ 5.x, aarch64, SSH enabled

## Building the RPM

All of it in **one** shell invocation, from the project root:

```bash
export PATH=/pfad/zu/sfdk/bin:$PATH
bash rpm/make-source-tarball.sh          # produces pseudopet-0.85-src.tar.gz
cp rpm/pseudopet.spec .sfdk/spec         # the spec pins to %{_builddir}/pseudopet-%{version}
sfdk config target=SailfishOS-5.1.0.11EA-aarch64
sfdk build --prepare -j8
```

Result: `RPMS/harbour-pseudopet-0.85-1.aarch64.rpm`.

Important: the RPM installs **from the Source0 tarball**, not from `src/`
directly. After every source change, run
`bash rpm/make-source-tarball.sh` again first.

## Installing on the phone

```bash
scp -o UserKnownHostsFile=~/.ssh/known_hosts -i ~/.ssh/deploy_key \
    RPMS/harbour-pseudopet-0.85-1.aarch64.rpm defaultuser@PHONE:/tmp/
ssh defaultuser@PHONE        # then as root:
rpm -Uvh --replacepkgs --nodeps /tmp/harbour-pseudopet-0.85-1.aarch64.rpm
```

Start from the app grid (icon "PseudoPet") or manually:

```bash
su - defaultuser -c 'export PYTHONUNBUFFERED=1 XDG_RUNTIME_DIR=/run/display \
  WAYLAND_DISPLAY=wayland-0 PULSE_SERVER=unix:/run/user/100000/pulse/native \
  DISPLAY=:0 XDG_SESSION_TYPE=wayland; \
  nohup /usr/bin/harbour-pseudopet > /tmp/pp-run.log 2>&1 &'
```

## Fast in-place deploy (source iteration only, without RPM)

```bash
scp src/main.py defaultuser@PHONE:/tmp/
# as root on the phone:
cp /tmp/main.py /usr/share/harbour-pseudopet/src/
rm -rf /usr/share/harbour-pseudopet/src/__pycache__
# restart (pattern split so that pkill -f does not match itself):
PAT='harbour-pseudo'pet/src/main[.]py; pkill -f "$PAT"
# then restart as shown above
```

Deliberately do not change the desktop file
(`desktop/org.beezi.harbour-pseudopet.desktop`):
`X-Nemo-Application-Type=no-invoker`, `Sandboxing=Disabled`,
bare `Exec=harbour-pseudopet` line (otherwise "is not elf binary").

## Headless tests (build PC)

```bash
cd src
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m py_compile *.py
```

Position/layout verification as described in `tests/` and in the header
notes of `README_TECHNICAL.md`: canvas 240×528, `BAND_Y = 104`, all
drawing clipped to the design window (240×320); `rh()/rhf()` are
**positions**, sizes/amplitudes always bare (or `rs`) — otherwise elements
drift +104 px downward (history of the butterfly/defense bug).

## Screenshot from the phone (diagnostics)

Lipstick requires the effective GID of the `privileged` group (995) from
the calling process. As root on the phone:

```bash
python3 -c "import os; os.setgroups([995,100000]); os.setgid(995); os.setuid(100000); \
os.environ['DBUS_SESSION_BUS_ADDRESS']='unix:path=/run/user/100000/dbus/user_bus_socket'; \
os.execvp('dbus-send',['dbus-send','--session','--print-reply', \
'--dest=org.nemomobile.lipstick','/org/nemomobile/lipstick/screenshot', \
'org.nemomobile.lipstick.saveScreenshot','string:/home/defaultuser/pp-shot.png'])"
```

Then `scp defaultuser@PHONE:/home/defaultuser/pp-shot.png .`

## Git repository

A new repository has been initialized (`main` branch). Create the remote
and push:

```bash
git remote add origin URL
git push -u origin main
```
