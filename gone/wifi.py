"""Wi-Fi par NetworkManager (nmcli) : liste des réseaux, connexion, état."""
from __future__ import annotations

import asyncio
import logging
import os

log = logging.getLogger(__name__)


def split_terse(line: str) -> list[str]:
    """Découpe une ligne « nmcli -t » : champs séparés par « : », « \\: » et « \\\\ » échappés."""
    fields, current, escaped = [], [], False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    fields.append("".join(current))
    return fields


def parse_networks(output: str) -> list[dict]:
    """Sortie de `nmcli -t -f IN-USE,SIGNAL,SECURITY,SSID device wifi list` -> réseaux uniques."""
    best: dict[str, dict] = {}
    for line in output.splitlines():
        parts = split_terse(line)
        if len(parts) < 4 or not parts[3]:
            continue
        in_use, signal, security, ssid = parts[0], parts[1], parts[2], parts[3]
        try:
            level = int(signal)
        except ValueError:
            level = 0
        entry = {"ssid": ssid, "signal": level, "secure": security.strip() not in ("", "--"),
                 "active": in_use.strip() == "*"}
        previous = best.get(ssid)
        if previous is None or entry["active"] or (level > previous["signal"] and not previous["active"]):
            best[ssid] = entry
    return sorted(best.values(), key=lambda n: (not n["active"], -n["signal"], n["ssid"].lower()))


def parse_status(output: str) -> dict:
    """Sortie de `nmcli -t -f TYPE,STATE,CONNECTION device status`."""
    status = {"wifi_available": False, "wifi_connected": False, "ssid": "", "ethernet": False}
    for line in output.splitlines():
        parts = split_terse(line)
        if len(parts) < 3:
            continue
        kind, state, connection = parts[0], parts[1], parts[2]
        connected = state.startswith("connected")
        if kind == "wifi":
            status["wifi_available"] = state != "unavailable"
            if connected:
                status["wifi_connected"] = True
                status["ssid"] = connection
        elif kind == "ethernet" and connected:
            status["ethernet"] = True
    return status


async def _run(*args: str, timeout: float = 45) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, env=dict(os.environ, LC_ALL="C"))
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, "", "délai dépassé"
    return proc.returncode or 0, out.decode(errors="replace"), err.decode(errors="replace")


class Wifi:
    async def networks(self) -> list[dict]:
        await _run("nmcli", "radio", "wifi", "on", timeout=10)
        code, out, err = await _run("nmcli", "-t", "-f", "IN-USE,SIGNAL,SECURITY,SSID",
                                    "device", "wifi", "list", "--rescan", "yes", timeout=30)
        if code != 0:
            raise RuntimeError(err.strip() or "recherche des réseaux impossible")
        return parse_networks(out)

    async def connect(self, ssid: str, password: str) -> tuple[bool, str]:
        _, before, _ = await _run("nmcli", "-t", "-f", "NAME", "connection", "show", timeout=10)
        existed = ssid in [split_terse(line)[0] for line in before.splitlines()]
        args = ["nmcli", "--wait", "30", "device", "wifi", "connect", ssid]
        if password:
            args += ["password", password]
        code, out, err = await _run(*args, timeout=45)
        if code == 0:
            log.info("Wi-Fi connecté à %s", ssid)
            return True, ""
        log.warning("Connexion Wi-Fi à %s en échec : %s", ssid, (err or out).strip())
        if not existed:      # ne pas laisser un profil au mauvais mot de passe
            await _run("nmcli", "connection", "delete", "id", ssid, timeout=10)
        message = (err or out).strip().lower()
        if "secrets were required" in message or "password" in message or "802-11-wireless-security" in message:
            return False, "Mot de passe incorrect."
        if "no network with ssid" in message:
            return False, "Réseau introuvable."
        return False, "Connexion impossible."

    async def status(self) -> dict:
        _, out, _ = await _run("nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "device", "status", timeout=10)
        status = parse_status(out)
        _, addresses, _ = await _run("hostname", "-I", timeout=5)
        status["ip"] = (addresses.split() or [""])[0]
        return status


class FakeWifi:
    """Mode développement : pas de matériel, réponses factices."""

    async def networks(self) -> list[dict]:
        await asyncio.sleep(0.3)
        return [{"ssid": "Maison", "signal": 82, "secure": True, "active": True},
                {"ssid": "Livebox-A1B2", "signal": 64, "secure": True, "active": False},
                {"ssid": "Invités", "signal": 40, "secure": False, "active": False}]

    async def connect(self, ssid: str, password: str) -> tuple[bool, str]:
        await asyncio.sleep(0.5)
        return (True, "") if password != "faux" else (False, "Mot de passe incorrect.")

    async def status(self) -> dict:
        return {"wifi_available": True, "wifi_connected": True, "ssid": "Maison",
                "ethernet": False, "ip": "192.168.1.42"}
