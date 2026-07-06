from _bootstrap_paths import ROOT  # noqa: F401
import random
import unittest

from Agent_studenta import AgentStudenta, StanAgenta
from Kolejki_pietrowe import KolejkiPietrowe
from Menedzer_agentow import KonfiguracjaGrupyAgentow, MenedzerAgentow
from Modele_planow import BlokZajec, DzienPlanu, PlanZajec
from Loader_planow import RepozytoriumPlanow
from Silnik_windy import SilnikWindy
from Konfiguracja_windy import ParametryWindy
from Ustawienia_projektu import UstawieniaProjektu


class TestyAgentaIKolejek(unittest.TestCase):
    def setUp(self) -> None:
        plan = PlanZajec(
            plan_id="test_plan",
            rok=1,
            grupa=1,
            wariant_zrodlowy="test",
            dni=(
                DzienPlanu(
                    dzien="poniedzialek",
                    bloki=(
                        BlokZajec("08:00", "09:30", "Matematyka", 1.0),
                        BlokZajec("11:00", "12:30", "Ekonomia [wyklad]", 0.5),
                    ),
                ),
            ),
        )
        self.repo = RepozytoriumPlanow({"test_plan": plan})
        self.ustawienia = UstawieniaProjektu()
        self.agent = AgentStudenta(
            id_agenta="A1",
            pietro_domowe=4,
            plan=plan,
            ustawienia=self.ustawienia,
            seed_agenta=123,
        )

    def test_czy_jest_w_akademiku_jest_wyliczane_ze_stanu(self) -> None:
        self.assertTrue(self.agent.czy_jest_w_akademiku)
        self.agent.stan = StanAgenta.POZA_AKADEMIKIEM
        self.assertFalse(self.agent.czy_jest_w_akademiku)

    def test_przygotowanie_dnia(self) -> None:
        self.agent.przygotuj_dzien("poniedzialek")
        self.assertGreaterEqual(len(self.agent.decyzje_dnia), 1)
        self.assertGreaterEqual(len(self.agent.harmonogram_dnia), 1)

    def test_kolejka_pozycja(self) -> None:
        kolejki = KolejkiPietrowe()
        p1 = kolejki.dolacz("A1", 4, "dol")
        p2 = kolejki.dolacz("A2", 4, "dol")
        self.assertEqual(p1, 1)
        self.assertEqual(p2, 2)
        self.assertEqual(kolejki.pobierz_pozycje("A2", 4, "dol"), 2)

    def test_agent_dolacza_do_kolejki(self) -> None:
        self.agent.dolacz_do_kolejki("dol", tick=10, pozycja=1, cel_pietro=0)
        self.assertEqual(self.agent.stan, StanAgenta.CZEKA_NA_WINDE_W_DOL)
        self.assertEqual(self.agent.pozycja_w_kolejce, 1)

    def test_rozpoczecie_przejazdu_czysci_stan_kolejki(self) -> None:
        self.agent.dolacz_do_kolejki("dol", tick=10, pozycja=1, cel_pietro=0)
        self.agent.rozpocznij_przejazd_winda(tick=12)
        self.assertEqual(self.agent.stan, StanAgenta.JEDZIE_WINDA)
        self.assertIsNone(self.agent.pozycja_w_kolejce)
        self.assertIsNone(self.agent.kierunek_kolejki)
        self.assertIsNone(self.agent.tick_wejscia_do_kolejki)

    def test_prawdopodobienstwo_schodow_rosnie_z_czasem(self) -> None:
        p1 = self.ustawienia.prawdopodobienstwo_rezygnacji_schodami(4, "dol", 0)
        p2 = self.ustawienia.prawdopodobienstwo_rezygnacji_schodami(4, "dol", 20)
        self.assertGreaterEqual(p2, p1)

    def test_menedzer_tworzy_agentow(self) -> None:
        winda = SilnikWindy(
            parametry=ParametryWindy(
                liczba_pieter=10,
                pietro_startowe=0,
                ticki_przejazdu_na_pietro=3,
                ticki_postoju=2,
                maks_pojemnosc=4,
                poczatkowe_obciazenie=0,
            )
        )
        menedzer = MenedzerAgentow(self.repo, winda, self.ustawienia)
        menedzer.dodaj_grupe(
            KonfiguracjaGrupyAgentow(
                nazwa="g1",
                plan_id="test_plan",
                pietro_domowe=4,
                liczba_agentow=3,
            )
        )
        self.assertEqual(len(menedzer.agenci), 3)


if __name__ == "__main__":
    unittest.main()
