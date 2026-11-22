"""Cartouches : détection de l'insertion et du retrait, copie du jeu dans un dossier neuf.

Chaque insertion reçoit un numéro de génération et son propre dossier. Une copie
interrompue ou dépassée par un changement de cartouche est jetée : le jeu servi
correspond toujours à la cartouche présente.
"""
from __future__ import annotations

import asyncio
import logging
import os
import secrets
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

log = logging.getLogger(__name__)

POLL_SECONDS = 1.0
FS_WAIT_SECONDS = 6.0
FAT_TYPES = ("vfat", "msdos")


@dataclass(frozen=True)
class Media:
    """Ce qui se trouve dans le lecteur à un instant donné."""
    disk: str                    # /dev/sda
    size: int                    # en secteurs
    fs_dev: str | None = None    # périphérique FAT identifié par udev
    fallback_dev: str | None = None   # à essayer si udev n'a rien identifié
    ident: str = ""              # identifiant du système de fichiers, s'il est connu


@dataclass(frozen=True)
class Card:
    """État exposé au reste du programme."""
    status: str = "none"         # none | copying | ready | error
    game_id: str = ""
    game_dir: Path | None = None


def same_media(a: Media | None, b: Media | None) -> bool:
    if a is None or b is None:
        return a is b
    if (a.disk, a.size) != (b.disk, b.size):
        return False
    return not (a.ident and b.ident and a.ident != b.ident)


Probe = Callable[[], "Media | None"]
Copier = Callable[[str, Path], Awaitable[bool]]


class CardWatcher:
    def __init__(self, probe: Probe, copier: Copier, games_dir: Path, entry: str,
                 on_change: Callable[[Card], None]):
        self._probe = probe
        self._copier = copier
        self._games_dir = games_dir
        self._entry = entry
        self._on_change = on_change
        self._kick = asyncio.Event()
        self._media_changed = False
        self._media: Media | None = None
        self._generation = 0
        self._copy_task: asyncio.Task | None = None
        self.card = Card()

    def notify(self, media_changed: bool = False) -> None:
        """À appeler sur un événement udev : relance une vérification immédiate."""
        if media_changed:
            self._media_changed = True
        self._kick.set()

    async def run(self) -> None:
        await asyncio.to_thread(self._wipe_games)
        while True:
            try:
                await self.tick()
            except Exception:
                log.exception("Erreur pendant la vérification de la cartouche")
            try:
                await asyncio.wait_for(self._kick.wait(), POLL_SECONDS)
            except asyncio.TimeoutError:
                pass
            self._kick.clear()

    async def tick(self) -> None:
        media = await asyncio.to_thread(self._probe)
        changed, self._media_changed = self._media_changed, False
        if not changed and same_media(media, self._media):
            if media is not None:
                self._media = media          # garde l'identifiant le plus récent
            return
        log.info("Cartouche : %s -> %s", _describe(self._media), _describe(media))
        self._media = media
        self._generation += 1
        if self._copy_task:
            self._copy_task.cancel()
            self._copy_task = None
        old = self.card
        self._set(Card("copying") if media else Card())
        if old.game_dir:
            await asyncio.to_thread(shutil.rmtree, old.game_dir, True)
        if media:
            self._copy_task = asyncio.create_task(self._copy(media, self._generation))

    async def _copy(self, media: Media, generation: int) -> None:
        dest = self._games_dir / f"{generation:04d}-{secrets.token_hex(4)}"
        try:
            waited = 0.0
            while media.fs_dev is None and waited < FS_WAIT_SECONDS:
                await asyncio.sleep(0.3)
                waited += 0.3
                current = await asyncio.to_thread(self._probe)
                if current is None or generation != self._generation:
                    return
                media = current
            device = media.fs_dev or media.fallback_dev or media.disk
            ok = False
            for attempt in (1, 2):       # un faux contact à l'insertion est fréquent : on réessaie
                await asyncio.to_thread(shutil.rmtree, dest, True)
                dest.mkdir(parents=True)
                ok = await self._copier(device, dest)
                if ok or generation != self._generation:
                    break
                log.warning("Copie de la cartouche en échec (essai %d)", attempt)
                await asyncio.sleep(0.5)
            if generation != self._generation:
                return
            has_game = (dest / self._entry).is_file()
            if has_game:
                if not ok:
                    log.warning("Copie incomplète mais jeu présent : cartouche acceptée")
                log.info("Jeu prêt : %s", dest)
                self._set(Card("ready", dest.name, dest))
            else:
                log.warning("Aucun jeu trouvé sur la cartouche (%s absent)", self._entry)
                await asyncio.to_thread(shutil.rmtree, dest, True)
                self._set(Card("error"))
        except asyncio.CancelledError:
            await asyncio.shield(asyncio.to_thread(shutil.rmtree, dest, True))
            raise
        except Exception:
            log.exception("Erreur pendant la copie de la cartouche")
            if generation == self._generation:
                self._set(Card("error"))

    def _set(self, card: Card) -> None:
        if card != self.card:
            self.card = card
            self._on_change(card)

    def _wipe_games(self) -> None:
        shutil.rmtree(self._games_dir, ignore_errors=True)
        self._games_dir.mkdir(parents=True, exist_ok=True)


def _describe(media: Media | None) -> str:
    return "aucune" if media is None else f"{media.disk} ({media.size} secteurs)"


# ---- accès au matériel -------------------------------------------------------

def make_copier(timeout: float) -> Copier:
    async def copy(device: str, dest: Path) -> bool:
        # mcopy lit la FAT sans monter la carte : rien à démonter si elle est arrachée.
        env = dict(os.environ, MTOOLS_SKIP_CHECK="1")
        proc = await asyncio.create_subprocess_exec(
            "mcopy", "-s", "-n", "-i", device, "::*", f"{dest}/",
            stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE, env=env)
        try:
            _, err = await asyncio.wait_for(proc.communicate(), timeout)
        except asyncio.TimeoutError:
            log.warning("Copie trop longue (> %ds), abandonnée", timeout)
            err = b""
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
        if proc.returncode != 0:
            log.warning("mcopy code %s : %s", proc.returncode, err.decode(errors="replace").strip()[-300:])
        return proc.returncode == 0
    return copy


def _root_disk() -> str | None:
    """Disque portant le système (jamais traité comme une cartouche)."""
    try:
        with open("/proc/mounts") as mounts:
            source = next((line.split()[0] for line in mounts if line.split()[1] == "/"), "")
        name = os.path.basename(os.path.realpath(source))
        sys_path = os.path.realpath(f"/sys/class/block/{name}")
        if os.path.exists(os.path.join(sys_path, "partition")):
            name = os.path.basename(os.path.dirname(sys_path))
        return f"/dev/{name}"
    except (OSError, IndexError):
        return None


def make_probe() -> Probe:
    import pyudev

    context = pyudev.Context()
    root_disk = _root_disk()
    tuned: set[str] = set()

    def probe() -> Media | None:
        for disk in sorted(context.list_devices(subsystem="block", DEVTYPE="disk"),
                           key=lambda d: d.sys_name):
            node = disk.device_node
            if disk.get("ID_BUS") != "usb" or not node or node == root_disk:
                continue
            if disk.sys_name not in tuned:
                tuned.add(disk.sys_name)
                try:    # le noyau vérifie la présence d'une carte deux fois par seconde
                    Path(f"/sys/block/{disk.sys_name}/events_poll_msecs").write_text("500")
                except OSError:
                    pass
            try:        # ouvrir le lecteur force le noyau à revérifier le média
                os.close(os.open(node, os.O_RDONLY | os.O_NONBLOCK))
            except OSError:
                pass
            try:
                size = int(Path(f"/sys/class/block/{disk.sys_name}/size").read_text())
            except (OSError, ValueError):
                continue
            if size <= 0:
                continue
            parts = sorted(context.list_devices(subsystem="block", DEVTYPE="partition", parent=disk),
                           key=lambda d: d.sys_name)
            fat = next((p for p in parts if p.get("ID_FS_TYPE") in FAT_TYPES), None)
            if fat is None and disk.get("ID_FS_TYPE") in FAT_TYPES:
                fat = disk
            fallback = parts[0].device_node if parts else node
            ident = (fat.get("ID_FS_UUID") or "") if fat is not None else ""
            return Media(node, size, fat.device_node if fat is not None else None, fallback, ident)
        return None

    return probe
