import asyncio

from gone.app import App
from gone.cards import Card
from gone.config import Config


class FakeBrowser:
    def __init__(self):
        self.calls = []
        self.ok = True
        self.page = "page-1"

    async def navigate(self, url, fresh_origin=None, attempts=20):
        self.calls.append((url, fresh_origin))
        return self.ok

    async def page_id(self):
        return self.page


def make():
    browser, system_calls = FakeBrowser(), []

    async def system(action):
        system_calls.append(action)

    app = App(Config(settings_combo_seconds=0.05), browser, system)
    return app, browser, system_calls


async def send(app, kind, *args):
    app.post(kind, *args)
    await app.drain()


READY = Card("ready", "0001-abcd", None)
BASE = "http://localhost:8000"


def test_yellow_starts_the_game_only_when_a_cartridge_is_ready():
    async def scenario():
        app, browser, _ = make()
        await send(app, "button", 0, "yellow", True)
        assert browser.calls == [] and app.screen == "lobby"

        await send(app, "card", Card("copying"))
        await send(app, "button", 0, "yellow", True)
        assert browser.calls == []

        await send(app, "card", READY)
        await send(app, "button", 1, "yellow", True)      # n'importe quelle manette
        assert browser.calls == [(f"{BASE}/play/0001-abcd/htmlGame/index.html", BASE)]
        assert app.screen == "game"
    asyncio.run(scenario())


def test_removing_or_swapping_the_cartridge_during_a_game_returns_to_lobby():
    async def scenario():
        for after in (Card(), Card("copying"), Card("ready", "0002-ffff", None)):
            app, browser, _ = make()
            await send(app, "card", READY)
            await send(app, "button", 0, "yellow", True)
            await send(app, "card", after)
            assert app.screen == "lobby"
            assert browser.calls[-1] == (f"{BASE}/lobby/index.html", None)
    asyncio.run(scenario())


def test_reset_button():
    async def scenario():
        app, browser, _ = make()
        await send(app, "reset")                           # lobby -> réglages
        assert app.screen == "settings"
        await send(app, "button", 0, "yellow", True)       # sans effet dans les réglages
        assert app.screen == "settings"
        await send(app, "reset")                           # réglages -> lobby
        assert app.screen == "lobby"
        await send(app, "card", READY)
        await send(app, "button", 0, "yellow", True)
        await send(app, "reset")                           # jeu -> lobby
        assert app.screen == "lobby"
        assert browser.calls[-1][0] == f"{BASE}/lobby/index.html"
    asyncio.run(scenario())


def test_holding_blue_and_red_opens_settings():
    async def scenario():
        app, browser, _ = make()
        await send(app, "button", 0, "blue", True)
        await send(app, "button", 0, "red", True)
        await asyncio.sleep(0.1)
        await app.drain()
        assert app.screen == "settings"

        app, browser, _ = make()                           # relâché trop tôt : rien
        await send(app, "button", 0, "blue", True)
        await send(app, "button", 0, "red", True)
        await send(app, "button", 0, "red", False)
        await asyncio.sleep(0.1)
        await app.drain()
        assert app.screen == "lobby" and browser.calls == []
    asyncio.run(scenario())


def test_power_button_shuts_down_once():
    async def scenario():
        app, browser, system_calls = make()
        await send(app, "power")
        await send(app, "power")
        await send(app, "reset")
        assert system_calls == ["poweroff"]
        assert browser.calls == [(f"{BASE}/transition/index.html", None)]
        assert app.screen == "off"
    asyncio.run(scenario())


def test_failed_navigation_and_browser_restart_fall_back_to_lobby():
    async def scenario():
        app, browser, _ = make()
        browser.ok = False
        await send(app, "reset")
        assert app.screen == "lobby"

        browser.ok = True
        await send(app, "card", READY)
        await send(app, "button", 0, "yellow", True)
        assert app.screen == "game"
        await send(app, "browser_restarted")
        assert app.screen == "lobby"
    asyncio.run(scenario())
