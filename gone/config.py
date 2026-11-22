"""Configuration : valeurs par défaut, surchargées par /etc/gone/config.toml."""
from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

log = logging.getLogger(__name__)

# Chemin réel de la version en cours : résolu une fois au démarrage, pour qu'une
# mise à jour (bascule du lien /opt/gone/current) ne change rien avant le redémarrage.
ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    http_host: str = "127.0.0.1"
    http_port: int = 8000          # le lobby interroge http://localhost:8000 en dur
    cdp_port: int = 9222           # port de débogage de Chromium
    state_dir: Path = Path("/var/lib/gone")
    web_dir: Path = ROOT / "web"
    game_entry: str = "htmlGame/index.html"
    copy_timeout: float = 180.0
    gpio_reset: int = 17           # BCM, actif à l'état haut (ancien wiringPi 0)
    gpio_power: int = 3            # BCM, actif à l'état bas (ancien wiringPi 9)
    settings_combo_seconds: float = 3.0
    grab_gamepads: bool = True     # False : Chromium voit aussi les manettes (Gamepad API)
    dev: bool = False              # sans matériel : pas de manettes, GPIO, cartouche ni nmcli

    @property
    def games_dir(self) -> Path:
        return self.state_dir / "games"

    @property
    def base_url(self) -> str:
        return f"http://localhost:{self.http_port}"


def version() -> str:
    try:
        return (ROOT / "VERSION").read_text().strip() or "dev"
    except OSError:
        return "dev"


def load() -> Config:
    cfg = Config()
    path = Path(os.environ.get("GONE_CONFIG", "/etc/gone/config.toml"))
    if path.is_file():
        try:
            data = tomllib.loads(path.read_text())
        except (OSError, tomllib.TOMLDecodeError) as exc:
            log.error("Configuration %s illisible, valeurs par défaut utilisées : %s", path, exc)
            data = {}
        known = {f.name: f for f in fields(Config)}
        for key, value in data.items():
            if key not in known:
                log.warning("Clé de configuration inconnue ignorée : %s", key)
                continue
            current = getattr(cfg, key)
            try:
                setattr(cfg, key, type(current)(value))
            except (TypeError, ValueError):
                log.warning("Valeur invalide pour %s : %r", key, value)
    if os.environ.get("GONE_DEV") == "1":
        cfg.dev = True
    if os.environ.get("GONE_STATE_DIR"):
        cfg.state_dir = Path(os.environ["GONE_STATE_DIR"])
    return cfg
