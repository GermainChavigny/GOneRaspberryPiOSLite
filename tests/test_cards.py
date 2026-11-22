import asyncio
import shutil
import subprocess

import pytest

from gone import cards
from gone.cards import Card, CardWatcher, Media, make_copier, same_media

CARD_A = Media("/dev/sda", 1000, "/dev/sda1", "/dev/sda1", "AAAA")
CARD_B = Media("/dev/sda", 2000, "/dev/sda1", "/dev/sda1", "BBBB")


class Rig:
    """Lecteur et copie factices autour d'un vrai CardWatcher."""

    def __init__(self, tmp_path, games=("jeu",), delay=0.0, failures=0):
        self.media = None
        self.games = dict.fromkeys(["/dev/sda1"], games[0]) if games else {}
        self.delay = delay
        self.failures = failures
        self.copies = 0
        self.states = []
        self.watcher = CardWatcher(lambda: self.media, self.copy, tmp_path / "games",
                                   "htmlGame/index.html", self.states.append)
        self.watcher._wipe_games()

    async def copy(self, device, dest):
        self.copies += 1
        await asyncio.sleep(self.delay)
        if self.failures:
            self.failures -= 1
            return False
        content = self.games.get(device)
        if content:
            (dest / "htmlGame").mkdir()
            (dest / "htmlGame" / "index.html").write_text(content)
        return True

    async def settle(self):
        await self.watcher.tick()
        task = self.watcher._copy_task
        if task:
            await asyncio.gather(task, return_exceptions=True)


def test_same_media():
    assert same_media(None, None)
    assert not same_media(None, CARD_A)
    assert not same_media(CARD_A, CARD_B)
    # identifiant pas encore connu : toujours la même carte
    assert same_media(CARD_A, Media("/dev/sda", 1000))
    assert not same_media(CARD_A, Media("/dev/sda", 1000, ident="ZZZZ"))


def test_insert_then_remove(tmp_path):
    async def scenario():
        rig = Rig(tmp_path)
        await rig.settle()
        assert rig.states == []

        rig.media = CARD_A
        await rig.settle()
        card = rig.watcher.card
        assert [s.status for s in rig.states] == ["copying", "ready"]
        assert (card.game_dir / "htmlGame" / "index.html").read_text() == "jeu"

        await rig.settle()                       # rien n'a changé : pas de nouvelle copie
        assert rig.copies == 1

        rig.media = None
        await rig.settle()
        assert rig.watcher.card == Card()
        assert not card.game_dir.exists()        # l'ancien jeu est effacé
    asyncio.run(scenario())


def test_cartridge_without_game_is_an_error(tmp_path):
    async def scenario():
        rig = Rig(tmp_path, games=())
        rig.media = CARD_A
        await rig.settle()
        assert rig.watcher.card.status == "error"
        assert list((tmp_path / "games").iterdir()) == []
    asyncio.run(scenario())


def test_swap_during_copy_never_serves_the_first_game(tmp_path):
    async def scenario():
        rig = Rig(tmp_path, delay=0.2)
        rig.media = CARD_A
        await rig.watcher.tick()                 # copie de A en cours
        rig.games["/dev/sda1"] = "jeu B"
        rig.media = CARD_B
        await rig.settle()
        card = rig.watcher.card
        assert card.status == "ready"
        assert (card.game_dir / "htmlGame" / "index.html").read_text() == "jeu B"
        assert [p.name for p in (tmp_path / "games").iterdir()] == [card.game_id]
    asyncio.run(scenario())


def test_media_change_event_with_identical_card_forces_a_new_copy(tmp_path):
    async def scenario():
        rig = Rig(tmp_path)
        rig.media = CARD_A
        await rig.settle()
        first = rig.watcher.card
        rig.watcher.notify(media_changed=True)   # échange rapide vu par le noyau
        await rig.settle()
        second = rig.watcher.card
        assert second.status == "ready" and second.game_id != first.game_id
        assert not first.game_dir.exists()
    asyncio.run(scenario())


def test_failed_copy_is_retried(tmp_path):
    async def scenario():
        rig = Rig(tmp_path, failures=1)
        rig.media = CARD_A
        await rig.settle()
        assert rig.watcher.card.status == "ready" and rig.copies == 2
    asyncio.run(scenario())


def test_waits_for_the_filesystem_to_be_identified(tmp_path):
    async def scenario():
        rig = Rig(tmp_path)
        rig.media = Media("/dev/sda", 1000)      # carte vue, partition pas encore identifiée
        await rig.watcher.tick()
        await asyncio.sleep(0.1)
        rig.media = Media("/dev/sda", 1000, "/dev/sda1", "/dev/sda1", "AAAA")
        await asyncio.gather(rig.watcher._copy_task)
        assert rig.watcher.card.status == "ready"
    asyncio.run(scenario())


@pytest.mark.skipif(not (shutil.which("mcopy") and shutil.which("mkfs.vfat")), reason="mtools/dosfstools absents")
def test_real_mcopy_from_a_fat_image(tmp_path):
    image = tmp_path / "card.img"
    subprocess.run(["mkfs.vfat", "-C", str(image), "4096"], check=True, capture_output=True)
    source = tmp_path / "index.html"
    source.write_text("<h1>jeu</h1>")
    (tmp_path / "icon.png").write_bytes(b"png")
    subprocess.run(["mmd", "-i", str(image), "::htmlGame"], check=True)
    subprocess.run(["mcopy", "-i", str(image), str(source), "::htmlGame/index.html"], check=True)
    subprocess.run(["mcopy", "-i", str(image), str(tmp_path / "icon.png"), "::icon.png"], check=True)

    dest = tmp_path / "dest"
    dest.mkdir()
    assert asyncio.run(make_copier(30)(str(image), dest)) is True
    assert (dest / "htmlGame" / "index.html").read_text() == "<h1>jeu</h1>"
    assert (dest / "icon.png").read_bytes() == b"png"

    empty = tmp_path / "empty.img"
    empty.write_bytes(b"\0" * 4096)              # pas une FAT : échec propre
    other = tmp_path / "other"
    other.mkdir()
    assert asyncio.run(make_copier(30)(str(empty), other)) is False
