"""Manettes : lecture exclusive des manettes USB et envoi des touches par un clavier virtuel.

- Les manettes sont détectées au branchement et au débranchement, à tout moment.
- Chaque manette est « saisie » (grab) : Chromium ne la voit plus, il ne reçoit que
  les touches du clavier virtuel. Un appui n'arrive donc qu'une seule fois.
- Le joueur dépend du port USB (voir players.py), pas de l'ordre de branchement.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Callable

import evdev

from . import udevwatch
from .padlogic import EV_ABS, EV_KEY, PLAYER_KEYS, PadTranslator
from .players import PlayerStore

log = logging.getLogger(__name__)

VKBD_NAME = "G one Virtual Keyboard"
RESCAN_SECONDS = 2.0


@dataclass
class _Pad:
    dev: evdev.InputDevice
    port: str
    player: int
    translator: PadTranslator
    task: asyncio.Task | None = field(default=None, repr=False)


def is_gamepad(dev: evdev.InputDevice) -> bool:
    caps = dev.capabilities()
    keys = caps.get(EV_KEY, [])
    has_pad_buttons = any(0x120 <= k < 0x140 for k in keys)
    axes = {code for code, _ in caps.get(EV_ABS, [])}
    has_directions = {0, 1} <= axes or {16, 17} <= axes or any(544 <= k <= 547 for k in keys)
    return has_pad_buttons and has_directions


def port_of(dev: evdev.InputDevice) -> str:
    # phys ressemble à « usb-0000:01:00.0-1.3/input0 » : on garde la partie port.
    return (dev.phys or "").split("/")[0] or dev.uniq or dev.name


class GamepadManager:
    def __init__(self, store: PlayerStore, on_button: Callable[[int, str, bool], None], grab: bool = True):
        self._grab = grab
        self._store = store
        self._on_button = on_button
        self._pads: dict[str, _Pad] = {}
        self._not_pads: set[tuple] = set()
        self._kick = asyncio.Event()
        self._ui: evdev.UInput | None = None

    # ---- état public -------------------------------------------------------
    def players(self) -> list[dict]:
        return sorted(
            ({"player": p.player + 1, "name": p.dev.name, "port": p.port} for p in self._pads.values()),
            key=lambda d: d["player"],
        )

    def swap_players(self) -> None:
        self._store.swap()
        self._reassign()

    def release_all(self) -> None:
        for pad in self._pads.values():
            self._emit(pad, pad.translator.release_all())

    # ---- boucle principale -------------------------------------------------
    async def run(self) -> None:
        keys = sorted({k for mapping in PLAYER_KEYS for k in mapping.values()})
        self._ui = evdev.UInput({EV_KEY: keys}, name=VKBD_NAME)
        log.info("Clavier virtuel créé")
        monitor = udevwatch.watch("input", lambda _dev: self._kick.set())  # noqa: F841 (gardé en vie)
        try:
            while True:
                self._scan()
                try:
                    await asyncio.wait_for(self._kick.wait(), RESCAN_SECONDS)
                    await asyncio.sleep(0.3)     # laisse le périphérique finir d'apparaître
                except asyncio.TimeoutError:
                    pass
                self._kick.clear()
        finally:
            self.release_all()
            for pad in list(self._pads.values()):
                self._close(pad)
            self._ui.close()

    def _scan(self) -> None:
        paths = evdev.list_devices()
        stamps = set()
        for path in paths:
            if path in self._pads:
                continue
            try:
                st = os.stat(path)
            except OSError:
                continue
            stamp = (path, st.st_ino, st.st_ctime_ns)
            stamps.add(stamp)
            if stamp in self._not_pads:
                continue
            try:
                dev = evdev.InputDevice(path)
            except OSError:
                continue                         # pas encore prêt : nouvel essai au prochain tour
            if dev.name == VKBD_NAME or not is_gamepad(dev):
                dev.close()
                self._not_pads.add(stamp)
                continue
            self._add(dev)
        self._not_pads &= stamps

    def _add(self, dev: evdev.InputDevice) -> None:
        port = port_of(dev)
        player = self._store.assign(port, {p.player for p in self._pads.values()})
        if player is None:
            log.info("Manette ignorée (deux manettes déjà actives) : %s sur %s", dev.name, port)
            dev.close()
            return
        if self._grab:
            try:
                dev.grab()
            except OSError as exc:
                log.warning("Saisie exclusive impossible pour %s : %s", dev.path, exc)
        ranges = {code: (info.min, info.max) for code, info in dev.capabilities().get(EV_ABS, [])}
        pad = _Pad(dev, port, player, PadTranslator(ranges))
        self._pads[dev.path] = pad
        pad.task = asyncio.create_task(self._read(pad))
        log.info("Manette joueur %d : %s (%s, port %s)", player + 1, dev.name, dev.path, port)

    async def _read(self, pad: _Pad) -> None:
        try:
            async for event in pad.dev.async_read_loop():
                if event.type in (EV_KEY, EV_ABS):
                    self._emit(pad, pad.translator.feed(event.type, event.code, event.value))
        except OSError:
            pass                                 # manette débranchée
        finally:
            log.info("Manette joueur %d débranchée (%s)", pad.player + 1, pad.dev.path)
            self._emit(pad, pad.translator.release_all())
            self._pads.pop(pad.dev.path, None)
            self._close(pad)
            self._kick.set()

    def _close(self, pad: _Pad) -> None:
        try:
            pad.dev.close()
        except Exception:
            pass

    def _emit(self, pad: _Pad, changes: list[tuple[str, bool]]) -> None:
        if not changes or self._ui is None:
            return
        for name, down in changes:
            self._ui.write(EV_KEY, PLAYER_KEYS[pad.player][name], 1 if down else 0)
        self._ui.syn()
        for name, down in changes:
            try:
                self._on_button(pad.player, name, down)
            except Exception:
                log.exception("Erreur dans le traitement d'un bouton")

    def _reassign(self) -> None:
        self.release_all()
        taken: set[int] = set()
        for pad in sorted(self._pads.values(), key=lambda p: p.port):
            player = self._store.assign(pad.port, taken)
            pad.player = player if player is not None else pad.player
            taken.add(pad.player)
            log.info("Manette %s (port %s) -> joueur %d", pad.dev.name, pad.port, pad.player + 1)
