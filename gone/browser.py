"""Pilotage de Chromium par son port de débogage (protocole DevTools)."""
from __future__ import annotations

import asyncio
import json
import logging

import aiohttp

log = logging.getLogger(__name__)


class Browser:
    def __init__(self, port: int):
        self._base = f"http://127.0.0.1:{port}"

    async def _page(self, session: aiohttp.ClientSession) -> dict | None:
        async with session.get(f"{self._base}/json/list") as resp:
            targets = await resp.json(content_type=None)
        return next((t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")), None)

    async def page_id(self) -> str | None:
        """Identifiant de l'onglet : il change quand Chromium a redémarré."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
                page = await self._page(session)
                return page["id"] if page else None
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ValueError):
            return None

    async def navigate(self, url: str, fresh_origin: str | None = None, attempts: int = 20) -> bool:
        """Affiche `url`. Avec `fresh_origin`, vide d'abord le cache et les service workers
        de cette origine, pour qu'aucun fichier d'un jeu précédent ne soit resservi."""
        commands: list[tuple[str, dict, bool]] = []
        if fresh_origin:
            commands.append(("Network.clearBrowserCache", {}, False))
            commands.append(("Storage.clearDataForOrigin",
                             {"origin": fresh_origin, "storageTypes": "service_workers,cache_storage"}, False))
        commands.append(("Page.navigate", {"url": url}, True))
        for attempt in range(attempts):
            try:
                await self._run(commands)
                log.info("Chromium -> %s", url)
                return True
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ValueError, RuntimeError) as exc:
                if attempt == attempts - 1:
                    log.error("Navigation vers %s impossible : %s", url, exc)
                await asyncio.sleep(0.5)
        return False

    async def _run(self, commands: list[tuple[str, dict, bool]]) -> None:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
            page = await self._page(session)
            if page is None:
                raise RuntimeError("aucun onglet Chromium")
            async with session.ws_connect(page["webSocketDebuggerUrl"]) as ws:
                for number, (method, params, required) in enumerate(commands, start=1):
                    await ws.send_str(json.dumps({"id": number, "method": method, "params": params}))
                    while True:
                        message = await ws.receive(timeout=6)
                        if message.type != aiohttp.WSMsgType.TEXT:
                            raise RuntimeError("connexion DevTools fermée")
                        reply = json.loads(message.data)
                        if reply.get("id") == number:
                            break
                    failure = reply.get("error") or reply.get("result", {}).get("errorText")
                    if failure and required:
                        raise RuntimeError(f"{method} : {failure}")
                    if failure:
                        log.debug("%s ignoré : %s", method, failure)
