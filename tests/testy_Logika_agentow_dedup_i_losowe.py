from _bootstrap_paths import ROOT  # noqa: F401

import random
import unittest

from Konfiguracja_windy import ParametryWindy
from Loader_planow import RepozytoriumPlanow
from Menedzer_agentow import KonfiguracjaGrupyAgentow, MenedzerAgentow
from Modele_planow import DzienPlanu, PlanZajec
from Nawigacja_po_planie import zbuduj_harmonogram_przejazdow_agenta
from Silnik_windy import SilnikWindy
from Ustawienia_projektu import UstawieniaProjektu


class TestyLogikiAgentowDedupILosowe(unittest.TestCase):
    def _stworz_plan(self) -> PlanZajec:
        return PlanZajec(
            plan_id="test_plan",
            rok=1,
            grupa=1,
            wariant_zrodlowy="test",
            dni=(DzienPlanu(dzien="poniedzialek", bloki=tuple()),),
        )

    def _stworz_menedzera(self) -> MenedzerAgentow:
        plan = self._stworz_plan()
        repo = RepozytoriumPlanow({"test_plan": plan})
        ustawienia = UstawieniaProjektu()
        winda = SilnikWindy(
            parametry=ParametryWindy(
                liczba_pieter=15,
                pietro_startowe=0,
                ticki_przejazdu_na_pietro=4,
                ticki_postoju=4,
                maks_pojemnosc=6,
                poczatkowe_obciazenie=0,
            )
        )
        menedzer = MenedzerAgentow(repo, winda, ustawienia)
        menedzer.dodaj_grupe(KonfiguracjaGrupyAgentow("g1", "test_plan", 4, 2))
        return menedzer

    def test_tylko_pierwszy_agent_naciska_wezwanie(self):
        menedzer = self._stworz_menedzera()
        agenci = list(menedzer.agenci.values())

        menedzer._dolacz_agenta_do_kolejki(agenci[0], "dol", tick=1, cel_pietro=0, typ_akcji="wyjscie_z_akademika", czy_losowe=False)
        menedzer._dolacz_agenta_do_kolejki(agenci[1], "dol", tick=2, cel_pietro=0, typ_akcji="wyjscie_z_akademika", czy_losowe=False)

        self.assertEqual(menedzer.statystyki["liczba_nacisniec_wezwania"], 1)
        self.assertEqual(menedzer.statystyki["liczba_dolaczen_do_istniejacego_wezwania"], 1)

    def test_tylko_pierwszy_agent_wybiera_pietro_w_kabinie(self):
        menedzer = self._stworz_menedzera()
        agenci = list(menedzer.agenci.values())

        menedzer._dolacz_agenta_do_kolejki(agenci[0], "dol", tick=1, cel_pietro=0, typ_akcji="wyjscie_z_akademika", czy_losowe=False)
        menedzer._dolacz_agenta_do_kolejki(agenci[1], "dol", tick=2, cel_pietro=0, typ_akcji="wyjscie_z_akademika", czy_losowe=False)
        menedzer.silnik_windy.aktualne_pietro = 4
        menedzer.silnik_windy.czy_stoi_na_przystanku = True

        menedzer._wpusc_agentow_do_windy(4, tick=10)

        self.assertEqual(menedzer.statystyki["liczba_nacisniec_wyboru_kabiny"], 1)
        self.assertEqual(menedzer.statystyki["liczba_dolaczen_do_istniejacego_wyboru_kabiny"], 1)

    def test_losowe_akcje_moga_zawierac_przejazd_miedzy_pietrami(self):
        plan = self._stworz_plan()
        decyzje, akcje = zbuduj_harmonogram_przejazdow_agenta(
            plan=plan,
            dzien="poniedzialek",
            generator=random.Random(123),
            prawdopodobienstwo_losowego_cyklu_dnia=0.0,
            prawdopodobienstwo_losowego_przejazdu_wewnatrz_akademika=1.0,
            minimalna_liczba_przejazdow_wewnatrz=1,
            maksymalna_liczba_przejazdow_wewnatrz=1,
            pietro_domowe=4,
            minimalne_pietro_losowych_przejazdow_wewnatrz=1,
            maksymalne_pietro_losowych_przejazdow_wewnatrz=10,
            pietro_parteru=0,
        )

        typy = [a.typ_akcji for a in akcje]
        self.assertIn("przejazd_miedzy_pietrami", typy)
        self.assertIn("powrot_na_pietro_domowe", typy)


if __name__ == "__main__":
    unittest.main()
