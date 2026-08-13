from wallpaper_changer.i18n import Translator


def test_translator_falls_back_and_switches_language():
    translator = Translator("invalid")
    assert translator("change_now") == "Change now"
    translator.set_language("bn")
    assert translator("change_now") == "এখনই পরিবর্তন"
    assert translator("missing-key") == "missing-key"
