from _bootstrap_paths import ROOT  # noqa: F401
import random
import unittest

from Modele_planow import BlokZajec, DzienPlanu, PlanZajec
from Nawigacja_po_planie import (
    pobierz_aktywny_blok,
    pobierz_nastepny_blok,
    pobierz_pierwszy_blok_dnia,
    pobierz_ostatni_blok_dnia,
    policz_przerwe_miedzy_blokami,
    czy_przerwa_pozwala_na_powrot,
    zbuduj_plan_dnia_agenta,
)


class TestyNawigacjiPoPlanie(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = PlanZajec(
            plan_id="test_plan",
            rok=1,
            grupa=1,
            wariant_zrodlowy="test",
            dni=(
                DzienPlanu(
                    dzien="poniedzialek",
                    bloki=(
                        BlokZajec("08:00", "09:30", "Matematyka", 1.0),
                        BlokZajec("11:00", "12:30", "Wykład ekonomii [wyklad]", 0.5),
                        BlokZajec("15:00", "16:30", "Programowanie", 1.0),
                    ),
                ),
            ),
        )

    def test_pierwszy_i_ostatni_blok(self) -> None:
        self.assertEqual(pobierz_pierwszy_blok_dnia(self.plan, "poniedzialek").nazwa, "Matematyka")
        self.assertEqual(pobierz_ostatni_blok_dnia(self.plan, "poniedzialek").nazwa, "Programowanie")

    def test_aktywny_blok(self) -> None:
        blok = pobierz_aktywny_blok(self.plan, "poniedzialek", "08:15")
        self.assertIsNotNone(blok)
        self.assertEqual(blok.nazwa, "Matematyka")

    def test_nastepny_blok(self) -> None:
        blok = pobierz_nastepny_blok(self.plan, "poniedzialek", "09:31")
        self.assertIsNotNone(blok)
        self.assertEqual(blok.nazwa, "Wykład ekonomii [wyklad]")

    def test_przerwa(self) -> None:
        bloki = self.plan.dzien("poniedzialek").bloki
        przerwa = policz_przerwe_miedzy_blokami(bloki[0], bloki[1])
        self.assertEqual(przerwa, 90)

    def test_prog_powrotu(self) -> None:
        self.assertTrue(czy_przerwa_pozwala_na_powrot(120))
        self.assertFalse(czy_przerwa_pozwala_na_powrot(90))

    def test_plan_dnia_agenta_jest_powtarzalny_dla_tego_samego_seed(self) -> None:
        decyzje_1 = zbuduj_plan_dnia_agenta(self.plan, "poniedzialek", random.Random(123))
        decyzje_2 = zbuduj_plan_dnia_agenta(self.plan, "poniedzialek", random.Random(123))

        statusy_1 = [d.czy_agent_idzie for d in decyzje_1]
        statusy_2 = [d.czy_agent_idzie for d in decyzje_2]

        self.assertEqual(statusy_1, statusy_2)


if __name__ == "__main__":
    unittest.main()