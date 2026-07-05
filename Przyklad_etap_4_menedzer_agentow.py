from pathlib import Path

from Czas_symulacji import CzasSymulacji
from Konfiguracja_windy import ParametryWindy
from Loader_planow import wczytaj_repozytorium_planow
from Menedzer_agentow import KonfiguracjaGrupyAgentow, MenedzerAgentow
from Silnik_windy import SilnikWindy
from Ustawienia_projektu import UstawieniaProjektu


def main() -> None:
    repo = wczytaj_repozytorium_planow(Path("/mnt/data/plany_iie_rok1_recznie_poprawione_v2.zip"))
    ustawienia = UstawieniaProjektu()
    parametry = ParametryWindy(
        liczba_pieter=10,
        pietro_startowe=0,
        ticki_przejazdu_na_pietro=3,
        ticki_postoju=2,
        maks_pojemnosc=4,
        poczatkowe_obciazenie=0,
    )
    winda = SilnikWindy(parametry=parametry)
    czas = CzasSymulacji(dzien_tygodnia_startowy=0, sekunda_dnia_startowa=7 * 3600 + 40 * 60)

    menedzer = MenedzerAgentow(repo, winda, ustawienia)
    menedzer.dodaj_grupe(
        KonfiguracjaGrupyAgentow(
            nazwa="g1_p4",
            plan_id=repo.plan_ids()[0],
            pietro_domowe=4,
            liczba_agentow=5,
        )
    )

    for _ in range(3 * 3600):
        winda.krok()
        info = czas.tick_na_czas(winda.aktualny_tick)
        menedzer.krok(info)

        if info["sekunda"] == 0 and info["minuta"] % 15 == 0:
            snap = menedzer.snapshot()
            print(
                f"[{info['nazwa_dnia']} {info['czas_tekst']}] "
                f"pietro_windy={winda.aktualne_pietro} "
                f"kierunek={winda.kierunek.name} "
                f"kolejki={snap['kolejki']} "
                f"w_windzie={snap['liczba_agentow_w_windzie']}"
            )


if __name__ == "__main__":
    main()
