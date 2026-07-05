from pathlib import Path

from Loader_planow import wczytaj_repozytorium_planow


def main() -> None:
    domyslna_sciezka = Path("./Plany_zajec")
    repo = wczytaj_repozytorium_planow(domyslna_sciezka)

    print("=== Lista planów ===")
    for plan_id in repo.plan_ids():
        plan = repo.pobierz(plan_id)
        print(plan.opis_skrocony())

    print()
    wybrany_id = repo.plan_ids()[0]
    plan = repo.pobierz(wybrany_id)

    print(f"=== Szczegóły planu: {wybrany_id} ===")
    for dzien in plan.dni:
        print(f"\n{dzien.dzien.upper()}")
        if not dzien.czy_sa_zajecia:
            print("  brak zajęć")
            continue

        for blok in dzien.bloki:
            rodzaj = "obowiązkowe" if blok.czy_obowiazkowe else "nieobowiązkowe"
            print(
                f"  {blok.godzina_od}-{blok.godzina_do} | "
                f"{blok.nazwa} | {rodzaj} | "
                f"uczestnictwo={blok.wspolczynnik_uczestnictwa}"
            )


if __name__ == "__main__":
    main()
