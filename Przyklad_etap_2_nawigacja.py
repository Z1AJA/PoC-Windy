from pathlib import Path
import random

from Loader_planow import wczytaj_repozytorium_planow
from Nawigacja_po_planie import (
    czy_dzis_sa_zajecia,
    pobierz_aktywny_blok,
    pobierz_nastepny_blok,
    pobierz_pierwszy_blok_dnia,
    pobierz_ostatni_blok_dnia,
    zbuduj_plan_dnia_agenta,
    zbuduj_proste_okna_powrotu,
)


def main() -> None:
    sciezka = Path("/mnt/data/plany_iie_rok1_recznie_poprawione_v2.zip")
    repo = wczytaj_repozytorium_planow(sciezka)
    plan = repo.pobierz(repo.plan_ids()[0])

    dzien = "poniedzialek"
    generator = random.Random(12345)

    print(f"=== PLAN: {plan.opis_skrocony()} ===")
    print(f"Czy w {dzien} są zajęcia? {czy_dzis_sa_zajecia(plan, dzien)}")

    pierwszy = pobierz_pierwszy_blok_dnia(plan, dzien)
    ostatni = pobierz_ostatni_blok_dnia(plan, dzien)

    print("\n=== PIERWSZY I OSTATNI BLOK ===")
    print(pierwszy)
    print(ostatni)

    print("\n=== BLOK AKTYWNY O 09:00 ===")
    print(pobierz_aktywny_blok(plan, dzien, "09:00"))

    print("\n=== NASTĘPNY BLOK PO 09:00 ===")
    print(pobierz_nastepny_blok(plan, dzien, "09:00"))

    print("\n=== DECYZJE AGENTA NA CAŁY DZIEŃ ===")
    decyzje = zbuduj_plan_dnia_agenta(plan, dzien, generator)
    for decyzja in decyzje:
        print(decyzja.opis())

    print("\n=== OKNA POWROTU DO AKADEMIKA ===")
    generator_okna = random.Random(12345)
    for okno in zbuduj_proste_okna_powrotu(plan, dzien, generator_okna, prog_powrotu_minuty=120):
        print(okno)


if __name__ == "__main__":
    main()\n