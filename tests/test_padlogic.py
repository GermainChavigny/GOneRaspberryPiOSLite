from gone.padlogic import EV_ABS, EV_KEY, PadTranslator


def test_buttons_press_and_release():
    pad = PadTranslator()
    assert pad.feed(EV_KEY, 290, 1) == [("yellow", True)]
    assert pad.feed(EV_KEY, 290, 2) == []            # répétition automatique ignorée
    assert pad.feed(EV_KEY, 290, 0) == [("yellow", False)]
    assert pad.feed(EV_KEY, 999, 1) == []            # bouton inconnu


def test_stick_uses_old_thresholds_on_0_255():
    pad = PadTranslator({0: (0, 255), 1: (0, 255)})
    assert pad.feed(EV_ABS, 0, 127) == []
    assert pad.feed(EV_ABS, 0, 0) == [("left", True)]
    # gauche -> droite d'un coup : relâche d'abord, appuie ensuite
    assert pad.feed(EV_ABS, 0, 255) == [("left", False), ("right", True)]
    assert pad.feed(EV_ABS, 0, 127) == [("right", False)]
    assert pad.feed(EV_ABS, 1, 0) == [("up", True)]
    assert pad.feed(EV_ABS, 1, 255) == [("up", False), ("down", True)]


def test_hat_axis_range_minus_one_to_one():
    pad = PadTranslator({16: (-1, 1), 17: (-1, 1)})
    assert pad.feed(EV_ABS, 16, -1) == [("left", True)]
    assert pad.feed(EV_ABS, 16, 0) == [("left", False)]
    assert pad.feed(EV_ABS, 17, 1) == [("down", True)]


def test_two_sources_for_the_same_direction():
    pad = PadTranslator({0: (0, 255), 16: (-1, 1)})
    assert pad.feed(EV_ABS, 0, 0) == [("left", True)]
    assert pad.feed(EV_ABS, 16, -1) == []            # déjà à gauche
    assert pad.feed(EV_ABS, 0, 127) == []            # la croix tient encore la direction
    assert pad.feed(EV_ABS, 16, 0) == [("left", False)]


def test_release_all():
    pad = PadTranslator()
    pad.feed(EV_KEY, 288, 1)
    pad.feed(EV_ABS, 1, 255)
    assert pad.release_all() == [("blue", False), ("down", False)]
    assert pad.feed(EV_KEY, 288, 0) == []            # le relâchement réel n'ajoute rien
