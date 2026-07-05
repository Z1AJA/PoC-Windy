from pathlib import Path

from Agent_studenta import AgentStudenta
from Kolejki_pietrowe import KolejkiPietrowe
from Loader_planow import wczytaj_repozytorium_planow
from Ustawienia_projektu import UstawieniaProjektu


def main() -> None:
    repo = wczytaj_repozytorium_planow(Path("/mnt/data/plany_iie_rok1_recznie_poprawione_v2.zip"))
    plan = repo.pobierz(repo.plan_ids()[0])

    ustawienia = UstawieniaProjektu()
    agent = AgentStudenta(
        id_agenta="A_001",
        pietro_domowe=4,
        plan=plan,
        ustawienia=ustawienia,
        seed_agenta=123,
    )

    agent.przygotuj_dzien("poniedzialek")
    print("=== PLAN DNIA AGENTA ===")
    for decyzja in agent.decyzje_dnia:
        print(decyzja.opis())

    print("\nPlanowana minuta pierwszego wyjścia:")
    print(agent.planowana_minuta_pierwszego_wyjscia())

    kolejki = KolejkiPietrowe()
    pozycja = kolejki.dolacz(agent.id_agenta, pietro=agent.pietro_domowe, kierunek="dol")
    agent.dolacz_do_kolejki(kierunek="dol", tick=100, pozycja=pozycja, cel_pietro=0)

    print("\n=== SNAPSHOT AGENTA PO DOŁĄCZENIU DO KOLEJKI ===")
    print(agent.snapshot())
    print(kolejki.snapshot())

    for tick in [101, 105, 110, 120]:
        czy_rezygnuje = agent.czy_rezygnuje_i_idzie_schodami(tick)
        print(f"tick={tick} | rezygnacja={czy_rezygnuje} | stan={agent.stan.name}")
        if czy_rezygnuje:
            kolejki.usun(agent.id_agenta, pietro=agent.pietro_domowe, kierunek="dol")
            break

    print("\n=== SNAPSHOT AGENTA PO OCZEKIWANIU ===")
    print(agent.snapshot())
    print(kolejki.snapshot())


if __name__ == "__main__":
    main()
