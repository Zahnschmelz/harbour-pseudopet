#!/usr/bin/env python3
# keeper.py — PseudoPet auf Sailfish OS
# [SFOS-PORT] Hintergrund-Wächter als Ersatz für PetAlarmReceiver.java:
# Wird vom systemd-User-Timer alle 5 Minuten gestartet, liest den
# Spielstand, simuliert die vergangene Zeit mit der Original-Spiel-
# mathematik (main.Pet.simulate_offline) und sendet D-Bus-
# Benachrichtigungen, wenn das Pet bald schlüpft, sich entwickelt,
# kritisch wird oder ein Bedürfnis hat.
#
# Wichtig:
#   - Der Keeper schreibt NIE den Spielstand (nur seinen eigenen State).
#   - Läuft die App gerade (Heartbeat jünger als 60 s), schweigt der
#     Keeper – die App benachrichtigt selbst.
#   - Kein Netz, kein Display nötig (SDL-Dummy-Treiber).

import contextlib
import io
import json
import os
import sys
import time

# --- headless erzwingen, BEVOR pygame/main importiert wird -------------
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.argv = ["pseudopet-keeper"]

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import main  # noqa: E402  (nutzt dieselbe Spiellogik wie die App)
import sfdnotify  # noqa: E402

KEEPER_INTERVAL = 300.0        # muss zum systemd-Timer passen (5 min)
HEARTBEAT_MAX_AGE = 60.0       # App gilt als laufend, wenn jünger
EVOLVE_NOTIFY_WINDOW = main.EVO_NOTIF_LEAD + KEEPER_INTERVAL
LOOKAHEAD = main.DEATH_WARN_WINDOW  # 30 min Todes-Projektion

STATE_DIR = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
STATE_DIR = os.path.join(STATE_DIR, "pseudopet")
STATE_FILE = os.path.join(STATE_DIR, "keeper.json")


def heartbeat_path():
    try:
        return os.path.join(os.path.dirname(main.SAVE_FILE), ".heartbeat")
    except Exception:
        return None


def app_running():
    hp = heartbeat_path()
    if not hp or not os.path.exists(hp):
        return False
    try:
        return (time.time() - os.path.getmtime(hp)) < HEARTBEAT_MAX_AGE
    except Exception:
        return False


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"notified": {}}


def save_state(st):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2)
    except Exception as e:
        print("[keeper] State nicht speicherbar:", e)


def notified_recently(st, key, cooldown):
    ts = st["notified"].get(key, 0)
    return (time.time() - ts) < cooldown


def mark_notified(st, key):
    st["notified"][key] = time.time()


def quiet_hours():
    h = time.localtime().tm_hour
    return main.QUIET_HOUR_START <= h or h < main.QUIET_HOUR_END


def pet_name():
    n = "PseudoPet"
    try:
        if main.SAVE_FILE and os.path.exists(main.SAVE_FILE):
            with open(main.SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            n = (data.get("pet") or {}).get("name") or n
    except Exception:
        pass
    return n


def project_future(pet, world, seconds):
    """Grober Zukunfts-Lauf: stirbt das Pet innerhalb von `seconds`?"""
    horizont = 0.0
    step = main.OFFLINE_CHUNK
    # Simulations-Debug-Ausgaben unterdruecken (Journal-Spam)
    with contextlib.redirect_stdout(io.StringIO()):
        while horizont < seconds:
            pet.simulate_offline(step)
            horizont += step
            if pet.state in (main.STATE_DEAD, main.STATE_GHOST):
                return horizont
    return None


def run_once():
    st = load_state()

    if not os.path.exists(main.SAVE_FILE):
        print("[keeper] kein Spielstand - nichts zu tun")
        return

    try:
        with open(main.SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("[keeper] Spielstand unlesbar:", e)
        return

    pet_data = data.get("pet") or {}
    name = pet_data.get("name") or "PseudoPet"
    if pet_data.get("state") == main.STATE_DEAD:
        print("[keeper] Pet ist verstorben - keine Meldung mehr nötig")
        return

    # ---- Pet und Welt wie Game.load() rekonstruieren -------------------
    try:
        pet = main.Pet.from_dict(pet_data)
    except Exception as e:
        print("[keeper] Pet nicht wiederherstellbar:", e)
        return
    world = main.World()
    room = data.get("room", "indoor")
    world.room = room if room in ("indoor", "outdoor") else "indoor"
    pet._world = world
    pet.outdoor = (world.room == "outdoor")

    # ---- vergangene Zeit simulieren (Original-Mathematik) --------------
    saved_at = data.get("saved_at") or time.time()
    elapsed = min(max(time.time() - saved_at, 0.0), main.OFFLINE_MAX)
    if elapsed > 0:
        with contextlib.redirect_stdout(io.StringIO()):
            pet.simulate_offline(elapsed)

    notifications_on = bool(data.get("notifications_on", True))
    if not notifications_on:
        print("[keeper] Notifications in der App deaktiviert - tschüss")
        return

    # ---- App läuft gerade? Dann schweigen ------------------------------
    if app_running():
        print("[keeper] App läuft (Heartbeat frisch) - keine Meldungen")
        return

    title = main.NOTIFICATIONTITEL[0].format(name=name)

    # ---- 1) Tod / kritischer Zustand -----------------------------------
    if pet.state in (main.STATE_DEAD, main.STATE_GHOST):
        if not notified_recently(st, "dead", 6 * 3600):
            sfdnotify.notify("PseudoPet", "Oh nein...",
                             "%s ist geschieden. Komm, um dich zu verabschieden." % name)
            mark_notified(st, "dead")
    else:
        # Todes-Projektion auf Kopie des bereits simulierten Zustands:
        probe = main.Pet.from_dict(pet.to_dict())
        probe._world = world
        probe.outdoor = pet.outdoor
        die_in = project_future(probe, world, LOOKAHEAD)
        if die_in is not None and not notified_recently(st, "death", main.DEATH_WARN_MIN):
            sfdnotify.notify("PseudoPet", "Dringend!",
                             "%s geht es richtig schlecht - komm schnell zurück!" % name)
            mark_notified(st, "death")

    # ---- 2) Schlüpfen / Evolution (umgeht Ruhezeit wie in der App) ------
    if pet.state not in (main.STATE_DEAD, main.STATE_GHOST) and not pet.choice_pending \
            and pet.state != main.STATE_HATCHING:
        stage_times = {
            main.STAGE_EGG:   pet.hatch_time,
            main.STAGE_BABY:  pet.baby_time,
            main.STAGE_CHILD: pet.child_time,
            main.STAGE_TEEN:  pet.teen_time,
        }
        t_remaining = stage_times.get(pet.stage)
        if t_remaining is not None:
            remaining = t_remaining - pet.stage_timer
            if 0 < remaining <= EVOLVE_NOTIFY_WINDOW and \
                    not notified_recently(st, "evolve", KEEPER_INTERVAL):
                reason = "hatch" if pet.stage == main.STAGE_EGG else "evolve"
                headline = main.NOTIF_HEADLINE.get(reason,
                                                   main.NOTIF_HEADLINE["evolve"])
                import random as _r
                msg = _r.choice(main.MESSAGES.get(reason, ["Komm schnell zurück!"]))
                sfdnotify.notify("PseudoPet", headline,
                                 msg.format(name=name))
                mark_notified(st, "evolve")

    # ---- 3) Bedürfnisse (mit Ruhezeit + Cooldown) -----------------------
    need_msgs = {
        "hungry": lambda: pet.hunger >= main.HUNGER_WARN,
        "sick":   lambda: bool(pet.sick),
        "poop":   lambda: getattr(pet, "poops", 0) >= main.POOP_WARN,
        "happy":  lambda: pet.happiness <= main.HAPPY_WARN,
    }
    if pet.state not in (main.STATE_DEAD, main.STATE_GHOST) and not quiet_hours():
        for key, cond in need_msgs.items():
            if cond() and not notified_recently(st, key, main.NOTIF_COOLDOWN):
                import random as _r
                msg = _r.choice(main.MESSAGES.get(key, ["Komm zurück!"]))
                sfdnotify.notify("PseudoPet",
                                 main.NOTIFICATIONTITEL[0],
                                 msg.format(name=name))
                mark_notified(st, key)

    save_state(st)
    print("[keeper] fertig (elapsed=%.0fs, state=%s, hunger=%d)"
          % (elapsed, pet.state, int(pet.hunger)))


if __name__ == "__main__":
    try:
        run_once()
    except Exception as e:
        import traceback
        print("[keeper] FEHLER:", e)
        traceback.print_exc()
        sys.exit(1)
