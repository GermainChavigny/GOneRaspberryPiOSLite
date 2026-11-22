from gone.players import PlayerStore


def test_port_decides_the_player_whatever_the_plug_order(tmp_path):
    path = tmp_path / "players.json"
    store = PlayerStore(path)
    assert store.assign("usb-1.1", set()) == 0
    assert store.assign("usb-1.2", {0}) == 1

    # redémarrage : la manette du port 1.2 est vue en premier, elle reste joueur 2
    store = PlayerStore(path)
    assert store.assign("usb-1.2", set()) == 1
    assert store.assign("usb-1.1", {1}) == 0


def test_swap_is_saved(tmp_path):
    path = tmp_path / "players.json"
    store = PlayerStore(path)
    store.assign("usb-1.1", set())
    store.assign("usb-1.2", {0})
    store.swap()
    assert PlayerStore(path).ports == {"usb-1.1": 1, "usb-1.2": 0}


def test_unknown_third_port_gets_a_free_slot_without_being_saved(tmp_path):
    store = PlayerStore(tmp_path / "players.json")
    store.assign("usb-1.1", set())
    store.assign("usb-1.2", {0})
    assert store.assign("usb-1.3", {0}) == 1         # port 1.2 débranché : place libre
    assert store.assign("usb-1.3", {0, 1}) is None   # deux manettes déjà actives
    assert "usb-1.3" not in store.ports


def test_corrupted_file_is_ignored(tmp_path):
    path = tmp_path / "players.json"
    path.write_text("{pas du json")
    assert PlayerStore(path).ports == {}
