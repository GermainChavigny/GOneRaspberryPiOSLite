"""Serveur HTTP local : pages (lobby, menu), jeu de la cartouche et API du menu."""
from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
from pathlib import Path

from aiohttp import web

from . import config

log = logging.getLogger(__name__)

for _ext, _type in {".js": "text/javascript", ".mjs": "text/javascript", ".wasm": "application/wasm",
                    ".json": "application/json", ".webp": "image/webp", ".webm": "audio/webm",
                    ".ogg": "audio/ogg", ".m4a": "audio/mp4", ".svg": "image/svg+xml",
                    ".woff2": "font/woff2"}.items():
    mimetypes.add_type(_type, _ext)


def _file(base: Path | None, tail: str) -> web.StreamResponse:
    """Sert un fichier situé sous `base`, sans jamais en sortir."""
    if base is None:
        raise web.HTTPNotFound()
    root = base.resolve()
    target = (root / tail).resolve()
    if target.is_dir():
        target = target / "index.html"
    if not target.is_file() or not target.is_relative_to(root):
        raise web.HTTPNotFound()
    return web.FileResponse(target)


@web.middleware
async def _no_cache(request: web.Request, handler):
    try:
        response = await handler(request)
    except web.HTTPException as exc:
        exc.headers["Cache-Control"] = "no-store"
        raise
    # Rien n'est gardé en cache : un nouveau jeu ne peut pas être remplacé par l'ancien.
    response.headers["Cache-Control"] = "no-store"
    return response


def build(cfg: config.Config, app, wifi, gamepads=None, updater=None) -> web.Application:
    routes = web.RouteTableDef()
    assets = cfg.web_dir / "assets"

    def game_dir() -> Path | None:
        return app.card.game_dir if app.card.status == "ready" else None

    # ---- jeu de la cartouche -------------------------------------------------
    @routes.get("/play/{game_id}/{tail:.*}")
    async def play(request: web.Request):
        if request.match_info["game_id"] != app.card.game_id:
            raise web.HTTPNotFound()
        return _file(game_dir(), request.match_info["tail"])

    # Adresses attendues par le lobby (et par l'ancien fonctionnement).
    @routes.get("/CompactFlash/{tail:.*}")
    async def compact_flash(request: web.Request):
        tail = request.match_info["tail"]
        if tail == "icon-ready.png":
            folder = game_dir()
            if folder is None:
                raise web.HTTPNotFound()
            return web.FileResponse(folder / "icon.png" if (folder / "icon.png").is_file()
                                    else assets / "icon-default.png")
        if tail == "icon-error.png":
            if app.card.status != "error":
                raise web.HTTPNotFound()
            return web.FileResponse(assets / "icon-error.png")
        return _file(game_dir(), tail)

    # ---- API du menu -------------------------------------------------------------
    @routes.get("/api/status")
    async def status(_request: web.Request):
        data = app.status()
        data["version"] = config.version()
        data["players"] = gamepads.players() if gamepads else []
        data["update"] = _read_json(cfg.state_dir / "update-status.json")
        return web.json_response(data)

    @routes.get("/api/network")
    async def network(_request: web.Request):
        return web.json_response(await wifi.status())

    @routes.get("/api/wifi/networks")
    async def wifi_networks(_request: web.Request):
        try:
            return web.json_response({"ok": True, "networks": await wifi.networks()})
        except Exception as exc:
            log.warning("Recherche Wi-Fi en échec : %s", exc)
            return web.json_response({"ok": False, "error": "Recherche des réseaux impossible."})

    @routes.post("/api/wifi/connect")
    async def wifi_connect(request: web.Request):
        try:
            body = await request.json()
            ssid, password = str(body["ssid"]), str(body.get("password", ""))
        except (ValueError, KeyError, TypeError):
            raise web.HTTPBadRequest()
        if not ssid or len(ssid.encode()) > 32 or len(password) > 63 or (password and len(password) < 8):
            return web.json_response({"ok": False, "error": "Le mot de passe doit faire 8 à 63 caractères."})
        ok, error = await wifi.connect(ssid, password)
        return web.json_response({"ok": ok, "error": error})

    @routes.post("/api/players/swap")
    async def players_swap(_request: web.Request):
        if gamepads:
            gamepads.swap_players()
        return web.json_response({"ok": True, "players": gamepads.players() if gamepads else []})

    @routes.post("/api/update")
    async def update(_request: web.Request):
        if updater is None:
            return web.json_response({"ok": True, "result": "current"})
        result = await updater()
        if result == "staged":
            asyncio.get_running_loop().call_later(3, app.post, "reboot")
        return web.json_response({"ok": result != "error", "result": result,
                                  "update": _read_json(cfg.state_dir / "update-status.json")})

    @routes.post("/api/exit")
    async def exit_settings(_request: web.Request):
        app.post("exit_settings")
        return web.json_response({"ok": True})

    # ---- pages statiques (lobby, transition, settings, assets) -----------------
    @routes.get("/{tail:.*}")
    async def static(request: web.Request):
        return _file(cfg.web_dir, request.match_info["tail"])

    application = web.Application(middlewares=[_no_cache])
    application.add_routes(routes)
    return application


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


async def serve(application: web.Application, host: str, port: int) -> web.AppRunner:
    runner = web.AppRunner(application, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, host, port, reuse_address=True).start()
    log.info("Serveur HTTP sur http://%s:%d", host, port)
    return runner
