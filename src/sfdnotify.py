# sfdnotify.py — PseudoPet auf Sailfish OS
# [SFOS-PORT] Benachrichtigungen über D-Bus (org.freedesktop.Notifications)
# ohne harte Python-Abhängigkeiten.
#
# Fallback-Kette:
#   1. python3-dbus (falls auf dem Gerät installiert)
#   2. dbus-send-Kommandozeile (Teil der dbus-utils, auf SFOS vorhanden)
#
# Genutzt von der App (Vordergrund) und vom systemd-Keeper (Hintergrund).
# Der Keeper läuft unter systemd --user; dort ist die Bus-Adresse über
# DBUS_SESSION_BUS_ADDRESS bzw. $XDG_RUNTIME_DIR/bus erreichbar.

import os
import subprocess
import sys


def _runtime_dir():
    rd = os.environ.get("XDG_RUNTIME_DIR")
    if rd:
        return rd
    return "/run/user/%d" % os.getuid()


def _session_bus_env():
    """Umgebung ergänzen, wenn DBUS_SESSION_BUS_ADDRESS fehlt (systemd-Keeper)."""
    env = dict(os.environ)
    if not env.get("DBUS_SESSION_BUS_ADDRESS"):
        cand = os.path.join(_runtime_dir(), "bus")
        if os.path.exists(cand):
            env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=" + cand
    return env


def notify(app_name, title, body, timeout_ms=15000):
    """Sendet eine Benachrichtigung. Gibt True bei Erfolg zurueck."""
    if _notify_dbus_python(app_name, title, body, timeout_ms):
        return True
    if _notify_dbus_send(app_name, title, body, timeout_ms):
        return True
    print("[sfdnotify] Konnte Benachrichtigung nicht senden "
          "(weder python3-dbus noch dbus-send verfuegbar)", file=sys.stderr)
    return False


def _notify_dbus_python(app_name, title, body, timeout_ms):
    try:
        import dbus  # noqa: python3-dbus
    except Exception:
        return False
    try:
        bus = dbus.SessionBus()
        iface = bus.get_object("org.freedesktop.Notifications",
                               "/org/freedesktop/Notifications")
        # App-Name mit Pet-Kontext: "PseudoPet" bleibt Signalgeber
        iface.Notify(app_name, 0, "", title, body, [],
                     {"x-nemo-icon": dbus.String("icon-lock-notifications")}
                     if False else {},
                     timeout_ms,
                     dbus_interface="org.freedesktop.Notifications")
        return True
    except Exception as e:
        print("[sfdnotify] python3-dbus fehlgeschlagen:", e, file=sys.stderr)
        return False


def _notify_dbus_send(app_name, title, body, timeout_ms):
    try:
        argv = [
            "dbus-send", "--session",
            "--dest=org.freedesktop.Notifications",
            "/org/freedesktop/Notifications",
            "org.freedesktop.Notifications.Notify",
            "string:%s" % app_name,
            "uint32:0",
            "string:",
            "string:%s" % title,
            "string:%s" % body,
            "array:string:",
            "dict:string:variant:",
            "int32:%d" % timeout_ms,
        ]
        r = subprocess.run(argv, env=_session_bus_env(),
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.PIPE, timeout=10)
        return r.returncode == 0
    except Exception as e:
        print("[sfdnotify] dbus-send fehlgeschlagen:", e, file=sys.stderr)
        return False


if __name__ == "__main__":
    ok = notify("PseudoPet",
                sys.argv[1] if len(sys.argv) > 1 else "PseudoPet-Test",
                sys.argv[2] if len(sys.argv) > 2 else "Hallo vom Keeper!")
    sys.exit(0 if ok else 1)
