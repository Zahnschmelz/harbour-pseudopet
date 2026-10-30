# screen.py — Design-Aufloesung + Skalierungs-Helfer
#
# [SFOS-PORT] Vollbild-Anpassung für lange Phone-Displays (z. B. Jolla
# Phone 2026, 1080x2340): Das Design bleibt 240x320 und wird zentriert
# in ein hoeheres virtuelles Canvas (VW x VH) gelegt. Der Zwischenraum
# (BAND_Y oben und unten) bleibt SCHWARZ (Letterbox-Look der Android-
# Vorlage): _fill_bg fuellt aussen schwarz, draw() beschneidet alles
# Zeichnen auf das Band; alle Spiel-Elemente sitzen pixelgenau wie im
# Original (Zeugnis: screenshots/device/panelfix_flach_knopfs_ganzunten.png).
#   rw(x)      -> Design-x bleibt unveraendert (Canvas-Breite == 240)
#   rh(y)      -> Design-y + Band-Offset (Vollbild-Zentrierung)
#   rs(n)      -> Design-Pixelgroesse (1:1, kein Verzerrung)
# Auf Desktop-Systemen (BAND_Y == 0) verhaelt sich alles exakt wie im
# Original.

import os
import pygame

DW, DH = 240, 320
VW, VH = DW, DH
BAND_Y = 0


def _fill_mode():
    """PSEUDOPET_FILL=0 erzwingt das klassische 240x320-Verhalten."""
    return os.environ.get("PSEUDOPET_FILL", "1").lower() not in ("0", "false", "no")


def set_canvas(vw, vh):
    """Virtuelles Canvas setzen (Auf-/Abrunden auf gerade Hoehe)."""
    global VW, VH, BAND_Y
    VW = max(DW, int(vw))
    VH = max(DH, int(vh))
    if VH % 2:
        VH += 1
    BAND_Y = (VH - DH) // 2


def compute_canvas_for(sw, sh):
    """Canvas-Masse fuer ein Display sw x sh (Seitenverhaeltnis beibehalten)."""
    if not sw or not sh:
        return DW, DH
    vh = int(round(DW * sh / sw))
    return DW, max(DH, vh)


def rw(x):  return int(round(x))
def rh(y):  return int(round(y)) + BAND_Y
def rs(n):  return max(1, int(round(n)))
def rp(x, y):   return (rw(x), rh(y))
def rrect(x, y, w, h): return pygame.Rect(rw(x), rh(y), rw(w), rs(h))
def rwf(x): return x
def rhf(y): return y + BAND_Y
def design_to_vy(y): return int(round(y)) + BAND_Y     # Design-y -> Canvas-y
def vy_to_design(vy): return vy - BAND_Y               # Canvas-y -> Design-y
