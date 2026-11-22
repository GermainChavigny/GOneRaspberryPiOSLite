import asyncio
from types import SimpleNamespace

from aiohttp.test_utils import TestClient, TestServer

from gone import web
from gone.cards import Card
from gone.config import Config
from gone.wifi import FakeWifi


def run(tmp_path, scenario):
    async def main():
        posted = []
        app = SimpleNamespace(card=Card(), status=lambda: {"screen": "lobby", "card": app.card.status},
                              post=lambda *event: posted.append(event))
        cfg = Config(state_dir=tmp_path / "state")
        async with TestClient(TestServer(web.build(cfg, app, FakeWifi()))) as client:
            await scenario(client, app, posted)
    asyncio.run(main())


def make_game(tmp_path, with_icon=True):
    game = tmp_path / "games" / "0001-abcd"
    (game / "htmlGame").mkdir(parents=True)
    (game / "htmlGame" / "index.html").write_text("JEU")
    if with_icon:
        (game / "icon.png").write_bytes(b"ICON")
    (tmp_path / "games" / "secret.txt").write_text("secret")
    return Card("ready", "0001-abcd", game)


def test_static_pages_are_never_cached(tmp_path):
    async def scenario(client, app, posted):
        for path in ("/lobby/index.html", "/settings/index.html", "/settings/app.js", "/transition/index.html"):
            response = await client.get(path)
            assert response.status == 200, path
            assert response.headers["Cache-Control"] == "no-store"
        assert (await client.get("/settings/app.js")).headers["Content-Type"].startswith("text/javascript")
        assert (await client.get("/nope.html")).status == 404
    run(tmp_path, scenario)


def test_lobby_icons_follow_the_cartridge_state(tmp_path):
    async def scenario(client, app, posted):
        assert (await client.get("/CompactFlash/icon-ready.png")).status == 404
        assert (await client.get("/CompactFlash/icon-error.png")).status == 404

        app.card = Card("error")
        assert (await client.get("/CompactFlash/icon-ready.png")).status == 404
        assert (await client.get("/CompactFlash/icon-error.png")).status == 200

        app.card = make_game(tmp_path)
        response = await client.get("/CompactFlash/icon-ready.png?r=1234")
        assert await response.read() == b"ICON"
        assert (await client.get("/CompactFlash/icon-error.png")).status == 404

        (app.card.game_dir / "icon.png").unlink()       # jeu sans icône : icône par défaut
        response = await client.get("/CompactFlash/icon-ready.png")
        assert response.status == 200 and (await response.read()).startswith(b"\x89PNG")
    run(tmp_path, scenario)


def test_game_is_served_only_under_its_own_id(tmp_path):
    async def scenario(client, app, posted):
        app.card = make_game(tmp_path)
        response = await client.get("/play/0001-abcd/htmlGame/index.html")
        assert await response.text() == "JEU"
        assert response.headers["Cache-Control"] == "no-store"
        assert (await client.get("/CompactFlash/htmlGame/index.html")).status == 200   # ancienne adresse
        assert (await client.get("/play/0000-old/htmlGame/index.html")).status == 404
        assert (await client.get("/play/0001-abcd/%2e%2e/secret.txt")).status == 404
        assert (await client.get("/play/0001-abcd/..%2Fsecret.txt")).status == 404

        app.card = Card()                               # cartouche retirée
        assert (await client.get("/play/0001-abcd/htmlGame/index.html")).status == 404
    run(tmp_path, scenario)


def test_api(tmp_path):
    async def scenario(client, app, posted):
        status = await (await client.get("/api/status")).json()
        assert status["screen"] == "lobby" and status["players"] == [] and "version" in status

        networks = await (await client.get("/api/wifi/networks")).json()
        assert networks["ok"] and networks["networks"][0]["ssid"] == "Maison"

        short = await (await client.post("/api/wifi/connect", json={"ssid": "Maison", "password": "abc"})).json()
        assert short["ok"] is False
        good = await (await client.post("/api/wifi/connect", json={"ssid": "Maison", "password": "motdepasse"})).json()
        assert good == {"ok": True, "error": ""}
        assert (await client.post("/api/wifi/connect", data="pas du json")).status == 400

        await client.post("/api/exit")
        assert posted == [("exit_settings",)]
    run(tmp_path, scenario)
