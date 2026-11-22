"""Machine à états de la console.

Deux états indépendants :
- l'écran affiché : lobby | game | settings | off ;
- la cartouche   : none | copying | ready | error (voir cards.py).

Tous les événements (manettes, boutons, cartouche, menu) passent par une seule file
et sont traités un par un : pas de course entre eux.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from .cards import Card
from .config import Config

log = logging.getLogger(__name__)

SETTINGS_COMBO = frozenset({"blue", "red"})
WATCHDOG_SECONDS = 3.0


class App:
    def __init__(self, cfg: Config, browser, system: Callable[[str], Awaitable[None]],
                 release_keys: Callable[[], None] = lambda: None):
        self.cfg = cfg
        self.browser = browser
        self._system = system               # system("poweroff") / system("reboot")
        self._release_keys = release_keys
        self.screen = "lobby"               # Chromium démarre sur le lobby
        self.card = Card()
        self._playing_id = ""
        self._held: dict[int, set[str]] = {}
        self._combo_tasks: dict[int, asyncio.Task] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._page_id: str | None = None

    def post(self, kind: str, *args) -> None:
        self._queue.put_nowait((kind, args))

    async def run(self) -> None:
        while True:
            kind, args = await self._queue.get()
            try:
                await getattr(self, f"_on_{kind}")(*args)
            except Exception:
                log.exception("Erreur pendant le traitement de l'événement %s", kind)

    async def drain(self) -> None:
        """Traite tous les événements en attente (pour les tests)."""
        while not self._queue.empty():
            kind, args = self._queue.get_nowait()
            await getattr(self, f"_on_{kind}")(*args)

    async def watchdog(self) -> None:
        """Si Chromium a redémarré (plantage), il est revenu sur le lobby : on se resynchronise."""
        while True:
            await asyncio.sleep(WATCHDOG_SECONDS)
            page_id = await self.browser.page_id()
            if page_id and self._page_id and page_id != self._page_id:
                self.post("browser_restarted")
            if page_id:
                self._page_id = page_id

    # ---- événements ----------------------------------------------------------
    async def _on_card(self, card: Card) -> None:
        self.card = card
        log.info("Cartouche : %s", card.status)
        if self.screen == "game" and (card.status != "ready" or card.game_id != self._playing_id):
            await self._show("lobby")

    async def _on_button(self, player: int, name: str, down: bool) -> None:
        held = self._held.setdefault(player, set())
        (held.add if down else held.discard)(name)
        if self.screen != "lobby":
            self._cancel_combo(player)
            return
        if down and name == "yellow" and self.card.status == "ready":
            self._cancel_combo(player)
            await self._show("game")
            return
        if held == SETTINGS_COMBO:
            if player not in self._combo_tasks:
                self._combo_tasks[player] = asyncio.create_task(self._combo_timer(player))
        else:
            self._cancel_combo(player)

    async def _combo_timer(self, player: int) -> None:
        await asyncio.sleep(self.cfg.settings_combo_seconds)
        self._combo_tasks.pop(player, None)
        self.post("combo", player)

    def _cancel_combo(self, player: int) -> None:
        task = self._combo_tasks.pop(player, None)
        if task:
            task.cancel()

    async def _on_combo(self, player: int) -> None:
        if self.screen == "lobby" and self._held.get(player) == SETTINGS_COMBO:
            await self._show("settings")

    async def _on_reset(self) -> None:
        log.info("Bouton reset (écran : %s)", self.screen)
        if self.screen in ("game", "settings"):
            await self._show("lobby")
        elif self.screen == "lobby":
            await self._show("settings")

    async def _on_exit_settings(self) -> None:
        if self.screen == "settings":
            await self._show("lobby")

    async def _on_power(self) -> None:
        await self._halt("poweroff")

    async def _on_reboot(self) -> None:
        await self._halt("reboot")

    async def _on_browser_restarted(self) -> None:
        if self.screen != "off":
            log.warning("Chromium a redémarré : retour au lobby")
            self.screen = "lobby"

    # ---- actions ---------------------------------------------------------------
    async def _halt(self, action: str) -> None:
        if self.screen == "off":
            return
        log.info("Arrêt demandé : %s", action)
        self.screen = "off"
        self._release_keys()
        await self.browser.navigate(f"{self.cfg.base_url}/transition/index.html", attempts=2)
        await self._system(action)

    async def _show(self, screen: str) -> None:
        base = self.cfg.base_url
        self._release_keys()
        if screen == "game":
            self._playing_id = self.card.game_id
            # Adresse unique par insertion : rien d'un jeu précédent ne peut être resservi.
            url = f"{base}/play/{self.card.game_id}/{self.cfg.game_entry}"
            ok = await self.browser.navigate(url, fresh_origin=base)
        else:
            url = f"{base}/{screen}/index.html"
            ok = await self.browser.navigate(url)
        if self.screen == "off":
            return
        self.screen = screen if ok else "lobby"
        self._page_id = await self.browser.page_id() or self._page_id

    def status(self) -> dict:
        return {"screen": self.screen, "card": self.card.status}
