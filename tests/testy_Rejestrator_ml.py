from _bootstrap_paths import *  # noqa: F401,F403

import unittest

from Rejestrator_ml import RejestratorObserwacjiML


class TestyRejestratoraML(unittest.TestCase):
    def test_rejestruje_wezwanie_z_pietra(self) -> None:
        r = RejestratorObserwacjiML()
        r.zarejestruj_wezwanie_z_pietra(
            tick=10,
            nazwa_dnia="poniedzialek",
            czas_tekst="08:15:00",
            pietro=4,
            kierunek="dol",
            obciazenie_windy=2,
        )
        rekord = r.rekordy_jako_dict()[0]
        self.assertEqual(rekord["typ_nacisniecia"], "wezwanie_z_pietra")
        self.assertEqual(rekord["pietro"], 4)
        self.assertEqual(rekord["kierunek"], "dol")
        self.assertEqual(rekord["obciazenie_windy"], 2)

    def test_rejestruje_wybor_z_kabiny(self) -> None:
        r = RejestratorObserwacjiML()
        r.zarejestruj_wybor_z_kabiny(
            tick=12,
            nazwa_dnia="poniedzialek",
            czas_tekst="08:16:00",
            pietro_docelowe=0,
            kierunek="dol",
            obciazenie_windy=3,
        )
        rekord = r.rekordy_jako_dict()[0]
        self.assertEqual(rekord["typ_nacisniecia"], "wybor_z_kabiny")
        self.assertEqual(rekord["pietro"], 0)
        self.assertEqual(rekord["kierunek"], "dol")


if __name__ == "__main__":
    unittest.main()
