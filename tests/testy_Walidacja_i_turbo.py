from _bootstrap_paths import ROOT  # noqa: F401

import random
import unittest
from pathlib import Path

from Agent_studenta import StanAgenta
from Czas_symulacji import CzasSymulacji
from Konfiguracja_windy import ParametryWindy
from Loader_planow import wczytaj_repozytorium_planow
from Menedzer_agentow import KonfiguracjaGrupyAgentow, MenedzerAgentow
from Nawigacja_po_planie import zbuduj_harmonogram_przejazdow_agenta
from Silnik_windy import SilnikWindy
from Ustawienia_projektu import UstawieniaProjektu


class TestyWalidacjiITurbo(unittest.TestCase):
    def _repo(self):
        return wczytaj_repozytorium_planow(Path(ROOT) / "data" / "Plany_zajec")

    def _ustawienia_stresowe(self):
        return UstawieniaProjektu(
            seed_glowny=12345,
            prawdopodobienstwo_losowego_cyklu_dnia=1.0,
            minimalna_liczba_losowych_cykli=1,
            maksymalna_liczba_losowych_cykli=2,
            prawdopodobienstwo_losowego_przejazdu_wewnatrz_akademika=1.0,
            minimalna_liczba_przejazdow_wewnatrz=1,
            maksymalna_liczba_przejazdow_wewnatrz=2,
        )

    def test_losowanie_pokrywa_wszystkie_typy_eventow(self):
        repo = self._repo()
        wymagane = {
            "losowe_wyjscie_z_akademika",
            "losowy_powrot_do_akademika",
            "losowy_przejazd_miedzy_pietrami",
        }
        znalezione = set()
        ustawienia = self._ustawienia_stresowe()

        for plan_id in repo.plan_ids():
            plan = repo.pobierz(plan_id)
            for dzien in [d.dzien for d in plan.dni]:
                for seed in range(20):
                    _, akcje = zbuduj_harmonogram_przejazdow_agenta(
                        plan=plan,
                        dzien=dzien,
                        generator=random.Random(seed),
                        bufor_wyjscia_przed_zajeciami_minuty=ustawienia.bufor_wyjscia_przed_zajeciami_minuty,
                        prog_powrotu_do_akademika_minuty=ustawienia.prog_powrotu_do_akademika_minuty,
                        prawdopodobienstwo_losowego_cyklu_dnia=ustawienia.prawdopodobienstwo_losowego_cyklu_dnia,
                        minimalna_liczba_losowych_cykli=ustawienia.minimalna_liczba_losowych_cykli,
                        maksymalna_liczba_losowych_cykli=ustawienia.maksymalna_liczba_losowych_cykli,
                        min_czas_poza_akademikiem_minuty=ustawienia.min_czas_poza_akademikiem_minuty,
                        max_czas_poza_akademikiem_minuty=ustawienia.max_czas_poza_akademikiem_minuty,
                        prawdopodobienstwo_losowego_przejazdu_wewnatrz_akademika=ustawienia.prawdopodobienstwo_losowego_przejazdu_wewnatrz_akademika,
                        minimalna_liczba_przejazdow_wewnatrz=ustawienia.minimalna_liczba_przejazdow_wewnatrz,
                        maksymalna_liczba_przejazdow_wewnatrz=ustawienia.maksymalna_liczba_przejazdow_wewnatrz,
                        min_czas_na_innym_pietrze_minuty=ustawienia.min_czas_na_innym_pietrze_minuty,
                        max_czas_na_innym_pietrze_minuty=ustawienia.max_czas_na_innym_pietrze_minuty,
                        najwczesniejsza_minuta_losowych_akcji=ustawienia.najwczesniejsza_minuta_losowych_akcji,
                        najpozniejsza_minuta_losowych_akcji=ustawienia.najpozniejsza_minuta_losowych_akcji,
                        minimalny_odstep_od_innych_akcji_minuty=ustawienia.minimalny_odstep_od_innych_akcji_minuty,
                        pietro_domowe=4,
                        minimalne_pietro_losowych_przejazdow_wewnatrz=ustawienia.minimalne_pietro_losowych_przejazdow_wewnatrz,
                        maksymalne_pietro_losowych_przejazdow_wewnatrz=ustawienia.maksymalne_pietro_losowych_przejazdow_wewnatrz,
                        pietro_parteru=ustawienia.pietro_parteru,
                    )
                    znalezione.update(a.typ_akcji for a in akcje if a.czy_losowe)
                    if wymagane.issubset(znalezione):
                        break
                if wymagane.issubset(znalezione):
                    break
            if wymagane.issubset(znalezione):
                break

        self.assertTrue(wymagane.issubset(znalezione), msg=f"Brakujące eventy: {wymagane - znalezione}")

    def test_krotki_turbo_run_jest_spojny(self):
        repo = self._repo()
        ustawienia = self._ustawienia_stresowe()
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
        plan_ids = repo.plan_ids()
        menedzer.dodaj_grupe(KonfiguracjaGrupyAgentow("g1_p4", plan_ids[0], 4, 6))
        if len(plan_ids) > 1:
            menedzer.dodaj_grupe(KonfiguracjaGrupyAgentow("g2_p8", plan_ids[1], 8, 5))
        czas = CzasSymulacji(dzien_tygodnia_startowy=0, sekunda_dnia_startowa=7 * 3600)

        for _ in range(8000):
            winda.krok()
            info = czas.tick_na_czas(winda.aktualny_tick)
            menedzer.krok(info)

            ids_w_windzie = list(menedzer.agenci_w_windzie)
            self.assertEqual(len(ids_w_windzie), len(set(ids_w_windzie)))

            for agent_id, agent in menedzer.agenci.items():
                if agent_id in menedzer.agenci_w_windzie:
                    self.assertEqual(agent.stan, StanAgenta.JEDZIE_WINDA)
                    self.assertFalse(agent.czy_czeka_w_kolejce)
                if agent.stan == StanAgenta.JEDZIE_WINDA:
                    self.assertIn(agent_id, menedzer.agenci_w_windzie)
                if agent.czy_czeka_w_kolejce:
                    self.assertIn(agent.stan, {StanAgenta.CZEKA_NA_WINDE_W_DOL, StanAgenta.CZEKA_NA_WINDE_W_GORE})

        snap = menedzer.snapshot()
        self.assertGreaterEqual(snap["statystyki"]["liczba_nacisniec_wezwania"], 1)
        self.assertGreaterEqual(snap["statystyki"]["liczba_nacisniec_wyboru_kabiny"], 1)


if __name__ == "__main__":
    unittest.main()
