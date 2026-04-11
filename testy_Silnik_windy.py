import unittest

from Konfiguracja_windy import ParametryWindy
from Kierunki_i_typy import Kierunek, ZrodloZgloszenia, TypZgloszenia
from Silnik_windy import SilnikWindy
from Zgloszenia_windy import ZgloszenieWindy


class TestySilnikaWindy(unittest.TestCase):
    def setUp(self):
        self.parametry = ParametryWindy(
            liczba_pieter=10,
            pietro_startowe=0,
            ticki_przejazdu_na_pietro=1,
            ticki_postoju=1,
            maks_pojemnosc=8,
            poczatkowe_obciazenie=0,
        )
        self.winda = SilnikWindy(parametry=self.parametry)

    def wykonaj_ticki(self, liczba_tickow: int) -> None:
        for _ in range(liczba_tickow):
            self.winda.krok()

    def test_pojedyncze_wezwanie_z_pietra(self):
        self.winda.dodaj_zgloszenie(ZgloszenieWindy(
            typ_zgloszenia=TypZgloszenia.WEZWANIE_Z_PIETRA,
            zrodlo=ZrodloZgloszenia.CZLOWIEK,
            tick_utworzenia=0,
            pietro=3,
            kierunek=Kierunek.GORA,
        ))

        self.wykonaj_ticki(6)
        stan = self.winda.snapshot()

        self.assertEqual(stan["aktualne_pietro"], 3)
        self.assertEqual(stan["liczba_aktywnych_zgloszen"], 0)

    def test_wybor_z_kabiny(self):
        self.winda.dodaj_zgloszenie(ZgloszenieWindy(
            typ_zgloszenia=TypZgloszenia.WYBOR_Z_KABINY,
            zrodlo=ZrodloZgloszenia.CZLOWIEK,
            tick_utworzenia=0,
            pietro=0,
            pietro_docelowe=5,
        ))

        self.wykonaj_ticki(10)
        stan = self.winda.snapshot()

        self.assertEqual(stan["aktualne_pietro"], 5)
        self.assertEqual(stan["liczba_aktywnych_zgloszen"], 0)

    def test_zatrzymanie_po_drodze(self):
        self.winda.dodaj_zgloszenie(ZgloszenieWindy(
            typ_zgloszenia=TypZgloszenia.WYBOR_Z_KABINY,
            zrodlo=ZrodloZgloszenia.CZLOWIEK,
            tick_utworzenia=0,
            pietro=0,
            pietro_docelowe=7,
        ))

        self.wykonaj_ticki(2)

        self.winda.dodaj_zgloszenie(ZgloszenieWindy(
            typ_zgloszenia=TypZgloszenia.WEZWANIE_Z_PIETRA,
            zrodlo=ZrodloZgloszenia.CZLOWIEK,
            tick_utworzenia=2,
            pietro=3,
            kierunek=Kierunek.GORA,
        ))

        self.wykonaj_ticki(10)
        stan = self.winda.snapshot()

        self.assertEqual(stan["aktualne_pietro"], 7)
        self.assertEqual(stan["liczba_aktywnych_zgloszen"], 0)

    def test_duplikat_zgloszenia_nie_tworzy_drugiego_aktywnego_przystanku(self):
        dodano_1 = self.winda.dodaj_zgloszenie(ZgloszenieWindy(
            typ_zgloszenia=TypZgloszenia.WEZWANIE_Z_PIETRA,
            zrodlo=ZrodloZgloszenia.CZLOWIEK,
            tick_utworzenia=0,
            pietro=4,
            kierunek=Kierunek.GORA,
        ))
        dodano_2 = self.winda.dodaj_zgloszenie(ZgloszenieWindy(
            typ_zgloszenia=TypZgloszenia.WEZWANIE_Z_PIETRA,
            zrodlo=ZrodloZgloszenia.SYSTEM,
            tick_utworzenia=1,
            pietro=4,
            kierunek=Kierunek.GORA,
        ))

        self.assertTrue(dodano_1)
        self.assertFalse(dodano_2)
        self.assertEqual(self.winda.liczba_aktywnych_zgloszen(), 1)

    def test_nieprawidlowe_pietro_powoduje_blad(self):
        with self.assertRaises(ValueError):
            self.winda.dodaj_zgloszenie(ZgloszenieWindy(
                typ_zgloszenia=TypZgloszenia.WEZWANIE_Z_PIETRA,
                zrodlo=ZrodloZgloszenia.CZLOWIEK,
                tick_utworzenia=0,
                pietro=99,
                kierunek=Kierunek.GORA,
            ))


if __name__ == "__main__":
    unittest.main()
