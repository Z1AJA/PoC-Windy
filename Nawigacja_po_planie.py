from __future__ import annotations

import random
from dataclasses import dataclass

from Modele_planow import BlokZajec, PlanZajec, czas_hhmm_na_minuty


@dataclass(frozen=True, slots=True)
class DecyzjaBlokuDnia:
    dzien: str
    blok: BlokZajec
    czy_agent_idzie: bool
    powod: str

    def opis(self) -> str:
        status = "IDZIE" if self.czy_agent_idzie else "NIE IDZIE"
        return (
            f"{self.dzien} | {self.blok.godzina_od}-{self.blok.godzina_do} | "
            f"{self.blok.nazwa} | {status} | {self.powod}"
        )


def pobierz_bloki_dnia(plan: PlanZajec, dzien: str) -> list[BlokZajec]:
    dzien_planu = plan.dzien(dzien)
    if dzien_planu is None:
        return []
    return list(dzien_planu.bloki)


def czy_dzis_sa_zajecia(plan: PlanZajec, dzien: str) -> bool:
    return len(pobierz_bloki_dnia(plan, dzien)) > 0


def pobierz_pierwszy_blok_dnia(plan: PlanZajec, dzien: str) -> BlokZajec | None:
    bloki = pobierz_bloki_dnia(plan, dzien)
    return bloki[0] if bloki else None


def pobierz_ostatni_blok_dnia(plan: PlanZajec, dzien: str) -> BlokZajec | None:
    bloki = pobierz_bloki_dnia(plan, dzien)
    return bloki[-1] if bloki else None


def pobierz_aktywny_blok(plan: PlanZajec, dzien: str, czas: str | int) -> BlokZajec | None:
    minuta = czas if isinstance(czas, int) else czas_hhmm_na_minuty(czas)
    for blok in pobierz_bloki_dnia(plan, dzien):
        if blok.minuta_startu <= minuta < blok.minuta_konca:
            return blok
    return None


def pobierz_nastepny_blok(plan: PlanZajec, dzien: str, czas: str | int) -> BlokZajec | None:
    minuta = czas if isinstance(czas, int) else czas_hhmm_na_minuty(czas)
    for blok in pobierz_bloki_dnia(plan, dzien):
        if blok.minuta_startu > minuta:
            return blok
    return None


def policz_przerwe_miedzy_blokami(pierwszy: BlokZajec, drugi: BlokZajec) -> int:
    return drugi.minuta_startu - pierwszy.minuta_konca


def czy_przerwa_pozwala_na_powrot(
    dlugosc_przerwy_minuty: int,
    prog_minut: int = 120,
) -> bool:
    return dlugosc_przerwy_minuty >= prog_minut


def decyzja_udzialu_w_bloku(
    blok: BlokZajec,
    generator: random.Random,
) -> tuple[bool, str]:
    if blok.wspolczynnik_uczestnictwa >= 1.0:
        return True, "blok_obowiazkowy"

    los = generator.random()
    if los <= blok.wspolczynnik_uczestnictwa:
        return True, f"wylosowano_udzial_{los:.4f}"
    return False, f"wylosowano_brak_udzialu_{los:.4f}"


def zbuduj_plan_dnia_agenta(
    plan: PlanZajec,
    dzien: str,
    generator: random.Random,
) -> list[DecyzjaBlokuDnia]:
    decyzje = []
    for blok in pobierz_bloki_dnia(plan, dzien):
        czy_idzie, powod = decyzja_udzialu_w_bloku(blok, generator)
        decyzje.append(
            DecyzjaBlokuDnia(
                dzien=dzien,
                blok=blok,
                czy_agent_idzie=czy_idzie,
                powod=powod,
            )
        )
    return decyzje
