"""Boutons de la console (reset et marche/arrêt) sur les GPIO, avec anti-rebond."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable

log = logging.getLogger(__name__)

STARTUP_GRACE = 3.0     # le bouton d'allumage peut encore être enfoncé juste après le démarrage
RESET_MIN_INTERVAL = 1.0


def start(reset_pin: int, power_pin: int, on_reset: Callable[[], None],
          on_power: Callable[[], None]) -> list:
    """Branche les deux boutons. Rend les objets à garder en vie (liste vide sans GPIO)."""
    try:
        from gpiozero import Button

        loop = asyncio.get_running_loop()
        started = time.monotonic()
        last_reset = 0.0

        def reset_pressed() -> None:
            nonlocal last_reset
            now = time.monotonic()
            if now - last_reset >= RESET_MIN_INTERVAL:
                last_reset = now
                loop.call_soon_threadsafe(on_reset)

        def power_held() -> None:
            if time.monotonic() - started >= STARTUP_GRACE:
                loop.call_soon_threadsafe(on_power)

        # Reset : relié au 3,3 V, résistance de rappel interne vers la masse.
        reset = Button(reset_pin, pull_up=False, bounce_time=0.05)
        reset.when_pressed = reset_pressed
        # Marche/arrêt : relié à la masse (le GPIO 3 a son propre rappel vers le 3,3 V
        # et réveille aussi le Pi éteint). Un appui de 0,3 s filtre les parasites.
        power = Button(power_pin, pull_up=True, bounce_time=0.05, hold_time=0.3)
        power.when_held = power_held
        log.info("Boutons : reset sur GPIO %d, marche/arrêt sur GPIO %d", reset_pin, power_pin)
        return [reset, power]
    except Exception as exc:
        log.warning("Boutons GPIO indisponibles : %s", exc)
        return []
