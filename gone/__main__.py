"""Point d'entrée du daemon : `python3 -m gone`."""
from __future__ import annotations

import asyncio
import logging
import signal
import sys

from . import buttons, config, udevwatch, web
from .app import App
from .browser import Browser
from .cards import CardWatcher, make_copier, make_probe
from .players import PlayerStore
from .wifi import FakeWifi, Wifi

log = logging.getLogger("gone")

HEALTHY_AFTER = 20.0


async def _system(action: str) -> None:
    proc = await asyncio.create_subprocess_exec("systemctl", action)
    await proc.wait()


async def _fake_system(action: str) -> None:
    log.info("[dev] systemctl %s", action)


def _make_updater(cfg: config.Config):
    async def run() -> str:
        proc = await asyncio.create_subprocess_exec("bash", str(config.ROOT / "scripts" / "update.sh"))
        code = await proc.wait()
        return {0: "current", 10: "staged"}.get(code, "error")
    return run


async def _mark_healthy(cfg: config.Config) -> None:
    # Remet à zéro le compteur d'échecs lu par scripts/guard.sh (retour arrière automatique).
    await asyncio.sleep(HEALTHY_AFTER)
    try:
        (cfg.state_dir / "failcount").write_text("0\n")
    except OSError as exc:
        log.warning("Compteur d'échecs non remis à zéro : %s", exc)
    await asyncio.Event().wait()


async def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stdout)
    cfg = config.load()
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    log.info("GOne %s%s", config.version(), " (mode dev, sans matériel)" if cfg.dev else "")

    gamepads = None
    keep_alive: list = []
    tasks: list[asyncio.Task] = []
    app = App(cfg, Browser(cfg.cdp_port), _fake_system if cfg.dev else _system,
              release_keys=lambda: gamepads.release_all() if gamepads else None)

    if cfg.dev:
        wifi, updater = FakeWifi(), None
    else:
        from .gamepads import GamepadManager

        wifi, updater = Wifi(), _make_updater(cfg)
        gamepads = GamepadManager(PlayerStore(cfg.state_dir / "players.json"),
                                  lambda player, name, down: app.post("button", player, name, down),
                                  grab=cfg.grab_gamepads)
        watcher = CardWatcher(make_probe(), make_copier(cfg.copy_timeout), cfg.games_dir,
                              cfg.game_entry, lambda card: app.post("card", card))
        keep_alive.append(udevwatch.watch(
            "block", lambda device: watcher.notify(device.get("DISK_MEDIA_CHANGE") == "1")))
        keep_alive.append(buttons.start(cfg.gpio_reset, cfg.gpio_power,
                                        lambda: app.post("reset"), lambda: app.post("power")))
        tasks += [asyncio.create_task(gamepads.run(), name="manettes"),
                  asyncio.create_task(watcher.run(), name="cartouche")]

    runner = await web.serve(web.build(cfg, app, wifi, gamepads, updater), cfg.http_host, cfg.http_port)
    tasks += [asyncio.create_task(app.run(), name="états"),
              asyncio.create_task(app.watchdog(), name="surveillance Chromium"),
              asyncio.create_task(_mark_healthy(cfg), name="santé")]

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stop.set)
    stopper = asyncio.create_task(stop.wait())
    done, _ = await asyncio.wait([*tasks, stopper], return_when=asyncio.FIRST_COMPLETED)

    code = 0
    for task in done:
        if task is not stopper:      # une tâche de fond ne doit jamais se terminer : systemd relancera
            log.error("Tâche « %s » arrêtée : %r", task.get_name(), task.exception())
            code = 1
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await runner.cleanup()
    return code


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
