"""Attribution des joueurs selon le port USB physique, mémorisée sur disque.

Le premier port vu devient le joueur 1, le deuxième le joueur 2, et cela ne change
plus (quel que soit l'ordre de branchement ou d'allumage), sauf échange depuis le menu.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

SLOTS = 2


class PlayerStore:
    def __init__(self, path: Path | None = None):
        self._path = path
        self.ports: dict[str, int] = {}
        if path and path.is_file():
            try:
                data = json.loads(path.read_text())
                self.ports = {str(p): int(s) for p, s in data.items() if int(s) in range(SLOTS)}
            except (OSError, ValueError, AttributeError) as exc:
                log.warning("Attribution des manettes illisible, réinitialisée : %s", exc)

    def assign(self, port: str, taken: set[int]) -> int | None:
        """Rend le joueur (0 ou 1) pour la manette du port donné, ou None s'il n'y a plus de place.

        `taken` : joueurs déjà occupés par les manettes actuellement branchées.
        """
        slot = self.ports.get(port)
        if slot is not None and slot not in taken:
            return slot
        if slot is None:
            bound = set(self.ports.values())
            for candidate in range(SLOTS):
                if candidate not in bound and candidate not in taken:
                    self.ports[port] = candidate
                    self._save()
                    return candidate
        # Port inconnu alors que les deux ports sont déjà mémorisés (ou place prise) :
        # attribution provisoire, non mémorisée.
        for candidate in range(SLOTS):
            if candidate not in taken:
                return candidate
        return None

    def swap(self) -> None:
        self.ports = {port: 1 - slot for port, slot in self.ports.items()}
        self._save()

    def reset(self) -> None:
        self.ports = {}
        self._save()

    def _save(self) -> None:
        if not self._path:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.ports, indent=2))
            tmp.replace(self._path)
        except OSError as exc:
            log.warning("Impossible d'enregistrer l'attribution des manettes : %s", exc)
