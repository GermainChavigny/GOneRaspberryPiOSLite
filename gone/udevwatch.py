"""Abonnement aux événements udev (branchements, changements de média) dans la boucle asyncio."""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

log = logging.getLogger(__name__)


def watch(subsystem: str, callback: Callable[[object], None]) -> object | None:
    """Appelle `callback(device)` à chaque événement udev du sous-système.

    Rend le moniteur (à garder en vie), ou None si udev n'est pas disponible :
    les modules appelants ont de toute façon une vérification périodique en secours.
    """
    try:
        import pyudev

        monitor = pyudev.Monitor.from_netlink(pyudev.Context())
        monitor.filter_by(subsystem)
        monitor.start()
    except Exception as exc:  # pas d'udev (conteneur, mode dev)
        log.warning("Événements udev « %s » indisponibles (%s) : vérification périodique seule", subsystem, exc)
        return None

    def drain() -> None:
        while True:
            try:
                device = monitor.poll(timeout=0)
            except Exception as exc:
                log.warning("Lecture udev en échec : %s", exc)
                return
            if device is None:
                return
            try:
                callback(device)
            except Exception:
                log.exception("Erreur dans le traitement d'un événement udev")

    asyncio.get_running_loop().add_reader(monitor.fileno(), drain)
    return monitor
