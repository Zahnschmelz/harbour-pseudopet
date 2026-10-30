#!/bin/bash
# pseudopet — Starter für Sailfish OS [SFOS-PORT]
APP=/usr/share/harbour-pseudopet

# Mitgeliefertes pygame (C-Erweiterungen) liegt in pylib; SDL2, SDL2_ttf und
# SDL2_mixer kommen aus den Sailfish-Systempaketen (kein LD_LIBRARY_PATH nötig).
export PYTHONPATH="$APP/pylib${PYTHONPATH:+:$PYTHONPATH}"

# Sailfish OS ist Wayland (kein X11/Xwayland); das Sailfish-SDL2 hat einen
# Wayland-Treiber, der D-Pad-Overlay der App läuft als Wayland-Fenster.
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-wayland}"
export SDL_HINT_VIDEO_ALLOW_SCREENSAVER=0

# ZENTRALE Einstellung auf Android-/libhybris-Geräten (Jolla Phone 2026, Mali):
# /usr/lib64/libEGL.so.1 ist die libhybris-Bibliothek, und die wählt ihr
# Plattform-Modul aus /usr/lib64/libhybris/ anhand von EGL_PLATFORM
# (eglplatform_wayland.so, _hwcomposer.so, _fbdev.so, _null.so). Fehlt die
# Variable, wird die null-Variante genommen und eglCreateWindowSurface
# assertet mit "ANativeWindow ... magic == ANDROID_NATIVE_WINDOW_MAGIC"
# (SIGABRT) – für jedes SDL2-Fenster, auch für den C-Test. Wayland ist das
# richtige Modul für Lipstick/Weston.
export EGL_PLATFORM="${EGL_PLATFORM:-wayland}"

# Wayland-Socket: in der Desktop-Sitzung vom Launcher gesetzt, hier nur als
# Absicherung für Startpfade ohne Sitzungsprofil (ssh, systemd-Timer).
if [ -z "$XDG_RUNTIME_DIR" ]; then
    export XDG_RUNTIME_DIR=/run/user/100000
fi
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"

# PulseAudio-Zugang: Desktop-Apps erben ihn aus der Sitzung; für ssh- und
# Timer-Start wird er hier gesetzt, damit SDL2_mixer nicht scheitert.
if [ -z "$PULSE_SERVER" ]; then
    for runtime in "$XDG_RUNTIME_DIR" /run/user/100000; do
        if [ -S "$runtime/pulse/native" ]; then
            export PULSE_SERVER="unix:$runtime/pulse/native"
            break
        fi
    done
fi
if [ -z "$PULSE_COOKIE" ]; then
    for runtime in "$XDG_RUNTIME_DIR" /run/user/100000; do
        if [ -f "$runtime/pulse/cookie" ]; then
            export PULSE_COOKIE="$runtime/pulse/cookie"
            break
        fi
    done
fi

exec /usr/bin/python3 "$APP/src/main.py" "$@"
