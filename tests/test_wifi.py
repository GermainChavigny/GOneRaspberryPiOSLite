from gone.wifi import parse_networks, parse_status, split_terse


def test_split_terse_handles_escaped_colons():
    assert split_terse(r"*:72:WPA2:Chez\: moi") == ["*", "72", "WPA2", "Chez: moi"]
    assert split_terse(r" :40::Back\\slash") == [" ", "40", "", "Back\\slash"]


def test_parse_networks_merges_duplicates_and_sorts():
    output = "\n".join([
        " :40:WPA2:Voisin",
        " :55:WPA2:Maison",
        "*:70:WPA2:Maison",
        " :90::Ouvert",
        " :30:WPA2:",                 # réseau masqué : ignoré
    ])
    networks = parse_networks(output)
    assert [n["ssid"] for n in networks] == ["Maison", "Ouvert", "Voisin"]
    assert networks[0] == {"ssid": "Maison", "signal": 70, "secure": True, "active": True}
    assert networks[1]["secure"] is False


def test_parse_status():
    status = parse_status("wifi:connected:Maison\nethernet:unavailable:\nloopback:connected (externally):lo\n")
    assert status == {"wifi_available": True, "wifi_connected": True, "ssid": "Maison", "ethernet": False}
    assert parse_status("wifi:unavailable:\n")["wifi_available"] is False
