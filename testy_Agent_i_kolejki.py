import unittest

from Agent_studenta import AgentStudenta, StanAgenta
from Kolejki_pietrowe import KolejkiPietrowe
from Modele_planow import BlokZajec, DzienPlanu, PlanZajec
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

    def test_prawdopodobienstwo_schodow_rosnie_z_czasem(self) -> None:
        p1 = self.ustawienia.prawdopodobienstwo_rezygnacji_schodami(4, "dol", 0)
        p2 = self.ustawienia.prawdopodobienstwo_rezygnacji_schodami(4, "dol", 20)
        self.assertGreaterEqual(p2, p1)


if __name__ == "__main__":
    unittest.main()
