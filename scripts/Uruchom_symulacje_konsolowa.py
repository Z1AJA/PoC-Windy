from _bootstrap_paths import *  # noqa: F401,F403

from pathlib import Path
import time

from Czas_symulacji import CzasSymulacji
from Dashboard_tekstowy import renderuj_dashboard, wyczysc_ekran
from Konfiguracja_windy import ParametryWindy
from Loader_planow import wczytaj_repozytorium_planow
from Logger_symulacji import LoggerSymulacji
from Menedzer_agentow import KonfiguracjaGrupyAgentow, MenedzerAgentow
from Model_energii import MonitorEnergiiWindy
from Silnik_windy import SilnikWindy
from Ustawienia_projektu import UstawieniaProjektu


def main() -> None:
    repo = wczytaj_repozytorium_planow(Path(__file__).resolve().parent.parent / "data" / "Plany_zajec")
    ustawienia = UstawieniaProjektu()
    parametry = ParametryWindy(
        liczba_pieter=15,
        pietro_startowe=0,
        ticki_przejazdu_na_pietro=4,
        ticki_postoju=4,
        maks_pojemnosc=6,
        poczatkowe_obciazenie=0,
    )
    winda = SilnikWindy(parametry=parametry)
    monitor_energii = MonitorEnergiiWindy()
    czas = CzasSymulacji(dzien_tygodnia_startowy=0, sekunda_dnia_startowa=7 * 3600 + 30 * 60)

    menedzer = MenedzerAgentow(repo, winda, ustawienia)
    logger = LoggerSymulacji(Path(__file__).resolve().parent.parent / "outputs" / "Debug_output")
    plan_ids = repo.plan_ids()

    menedzer.dodaj_grupe(KonfiguracjaGrupyAgentow("g1_p4", plan_ids[0], 4, 5))
    if len(plan_ids) > 1:
        menedzer.dodaj_grupe(KonfiguracjaGrupyAgentow("g2_p7", plan_ids[1], 7, 4))
    if len(plan_ids) > 2:
        menedzer.dodaj_grupe(KonfiguracjaGrupyAgentow("g3_p10", plan_ids[2], 10, 3))

    ostatni_eksport_dnia = None

    try:
        while True:
            winda.krok()
            monitor_energii.krok(winda.snapshot())
            czas_info = czas.tick_na_czas(winda.aktualny_tick)
            menedzer.krok(czas_info)
            logger.pobierz_nowe_zdarzenia_z_menedzera(menedzer)

            if ostatni_eksport_dnia != czas_info["nazwa_dnia"]:
                logger.eksportuj_plany_dnia_json(menedzer)
                logger.eksportuj_plany_dnia_txt(menedzer)
                ostatni_eksport_dnia = czas_info["nazwa_dnia"]

            if czas_info["sekunda"] == 0:
                logger.zapisz_probke(
                    czas_info=czas_info,
                    snapshot_windy=winda.snapshot(),
                    snapshot_menedzera=menedzer.snapshot(),
                    snapshot_energii=monitor_energii.snapshot(),
                )

            if czas_info["sekunda"] % 2 == 0:
                wyczysc_ekran()
                print(renderuj_dashboard(
                    czas_info=czas_info,
                    snapshot_windy=winda.snapshot(),
                    snapshot_menedzera=menedzer.snapshot(),
                    zdarzenia=menedzer.ostatnie_zdarzenia(12),
                    snapshot_energii=monitor_energii.snapshot(),
                ))
                print("\nPliki debug zapisują się do outputs/Debug_output (ignorowane przez git).")
                print("Ctrl+C aby zakończyć.")
                time.sleep(0.08)

    except KeyboardInterrupt:
        logger.eksportuj_probki_jsonl()
        logger.eksportuj_zdarzenia_jsonl()
        wyczysc_ekran()
        print("Symulacja zatrzymana przez użytkownika.")
        print("Wyeksportowano debug do outputs/Debug_output.")


if __name__ == "__main__":
    main()
