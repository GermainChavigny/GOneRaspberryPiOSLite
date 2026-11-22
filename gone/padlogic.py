"""Traduction des événements bruts d'une manette en boutons logiques, puis en touches.

Module sans dépendance matérielle (testable partout).
"""
from __future__ import annotations

EV_KEY, EV_ABS = 1, 3

# Boutons logiques : up, down, left, right, blue, red, yellow.
# 288-290 : manette « USB Gamepad » de la console (BTN_TRIGGER / THUMB / THUMB2).
# 304-308 : repli pour une manette de type Xbox. 544-547 : croix en boutons.
BUTTONS = {
    288: "blue", 289: "red", 290: "yellow",
    304: "blue", 305: "red", 307: "yellow", 308: "yellow",
    544: "up", 545: "down", 546: "left", 547: "right",
}

# Axes : stick (ABS_X / ABS_Y) et croix (ABS_HAT0X / ABS_HAT0Y) -> (sens négatif, sens positif)
AXES = {0: ("left", "right"), 1: ("up", "down"), 16: ("left", "right"), 17: ("up", "down")}

# Codes de touches Linux envoyés par le clavier virtuel, par joueur.
# Identique à l'ancien mapping xdotool : J1 = ZQSD + B/V/C, J2 = flèches + K/L/M.
# Le serveur X est forcé en disposition « us » pour que ces codes donnent ces lettres.
KEY_Z, KEY_Q, KEY_S, KEY_D, KEY_B, KEY_V, KEY_C = 44, 16, 31, 32, 48, 47, 46
KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_K, KEY_L, KEY_M = 103, 108, 105, 106, 37, 38, 50

PLAYER_KEYS = (
    {"up": KEY_Z, "down": KEY_S, "left": KEY_Q, "right": KEY_D,
     "blue": KEY_B, "red": KEY_V, "yellow": KEY_C},
    {"up": KEY_UP, "down": KEY_DOWN, "left": KEY_LEFT, "right": KEY_RIGHT,
     "blue": KEY_K, "red": KEY_L, "yellow": KEY_M},
)

# Part de la course d'un axe à partir de laquelle la direction compte
# (0,2 sur 0..255 donne ~51 / ~204, comme les anciens seuils 50 / 205).
AXIS_THRESHOLD = 0.2


class PadTranslator:
    """État d'une manette : reçoit ses événements, rend les changements de boutons logiques."""

    def __init__(self, abs_ranges: dict[int, tuple[int, int]] | None = None):
        self._ranges = abs_ranges or {}
        self._sources: dict[tuple[int, int], frozenset[str]] = {}
        self._active: frozenset[str] = frozenset()

    def feed(self, etype: int, code: int, value: int) -> list[tuple[str, bool]]:
        if etype == EV_KEY:
            name = BUTTONS.get(code)
            if name is None or value == 2:      # 2 = répétition automatique
                return []
            self._sources[(etype, code)] = frozenset([name]) if value else frozenset()
        elif etype == EV_ABS:
            names = AXES.get(code)
            if names is None:
                return []
            low, high = self._ranges.get(code, (0, 255))
            if high <= low:
                low, high = 0, 255
            margin = (high - low) * AXIS_THRESHOLD
            if value < low + margin:
                held = frozenset([names[0]])
            elif value > high - margin:
                held = frozenset([names[1]])
            else:
                held = frozenset()
            self._sources[(etype, code)] = held
        else:
            return []
        return self._diff()

    def release_all(self) -> list[tuple[str, bool]]:
        self._sources.clear()
        return self._diff()

    def _diff(self) -> list[tuple[str, bool]]:
        active = frozenset().union(*self._sources.values()) if self._sources else frozenset()
        # Relâchements d'abord : gauche -> droite donne « gauche relâché » puis « droite appuyé ».
        changes = [(n, False) for n in sorted(self._active - active)]
        changes += [(n, True) for n in sorted(active - self._active)]
        self._active = active
        return changes
