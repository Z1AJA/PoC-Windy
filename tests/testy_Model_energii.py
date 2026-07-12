from _bootstrap_paths import *  # noqa: F401,F403

import unittest

from Model_energii import MonitorEnergiiWindy, ParametryEnergetyczne


class TestyModeluEnergii(unittest.TestCase):
    def test_brak_zmiany_snapshot_nie_zuzywa_energii(self) -> None:
        m = MonitorEnergiiWindy()
        snap = {
            "aktualne_pietro": 0,
            "kierunek": "BEZRUCH",
            "czy_jedzie": False,
            "czy_stoi_na_przystanku": False,
            "obciazenie": 0,
            "maks_pojemnosc": 6,
            "liczba_aktywnych_zgloszen": 0,
        }
        m.krok(snap)
        m.krok(snap)
        self.assertEqual(m.snapshot()["energia_calkowita"], 0.0)

    def test_rozruch_i_jazda_zwiekszaja_energie(self) -> None:
        m = MonitorEnergiiWindy()
        m.krok({
            "aktualne_pietro": 0, "kierunek": "BEZRUCH", "czy_jedzie": False,
            "czy_stoi_na_przystanku": False, "obciazenie": 0, "maks_pojemnosc": 6,
            "liczba_aktywnych_zgloszen": 0,
        })
        m.krok({
            "aktualne_pietro": 0, "kierunek": "GORA", "czy_jedzie": True,
            "czy_stoi_na_przystanku": False, "obciazenie": 2, "maks_pojemnosc": 6,
            "liczba_aktywnych_zgloszen": 1,
        })
        m.krok({
            "aktualne_pietro": 1, "kierunek": "GORA", "czy_jedzie": True,
            "czy_stoi_na_przystanku": False, "obciazenie": 2, "maks_pojemnosc": 6,
            "liczba_aktywnych_zgloszen": 1,
        })
        snap = m.snapshot()
        self.assertGreater(snap["energia_calkowita"], 0.0)
        self.assertEqual(snap["liczba_rozruchow"], 1)
        self.assertEqual(snap["liczba_przejazdow_miedzy_pietrami"], 1)

    def test_postoj_dodaje_energie_postoju(self) -> None:
        m = MonitorEnergiiWindy()
        m.krok({
            "aktualne_pietro": 0, "kierunek": "BEZRUCH", "czy_jedzie": False,
            "czy_stoi_na_przystanku": False, "obciazenie": 0, "maks_pojemnosc": 6,
            "liczba_aktywnych_zgloszen": 0,
        })
        m.krok({
            "aktualne_pietro": 0, "kierunek": "BEZRUCH", "czy_jedzie": False,
            "czy_stoi_na_przystanku": True, "obciazenie": 0, "maks_pojemnosc": 6,
            "liczba_aktywnych_zgloszen": 0,
        })
        self.assertGreater(m.snapshot()["energia_postoju"], 0.0)


if __name__ == "__main__":
    unittest.main()
