from __future__ import annotations

import random
from dataclasses import dataclass

from Modele_planow import BlokZajec, PlanZajec, czas_hhmm_na_minuty, czas_minuty_na_hhmm


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


@dataclass(frozen=True, slots=True)
class AkcjaDniaAgenta:
    minuta: int
    typ_akcji: str
    opis: str
    czy_losowe: bool = False

    def minuta_hhmm(self) -> str:
        return czas_minuty_na_hhmm(self.minuta)


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


def _okna_pobytu_w_akademiku(
    akcje_bazowe: list[AkcjaDniaAgenta],
    najwczesniej: int,
    najpozniej: int,
) -> list[tuple[int, int]]:
    wynik = []
    akcje = sorted(akcje_bazowe, key=lambda a: (a.minuta, a.typ_akcji))
    jest_w_akademiku = True
    start_okna = 0

    for akcja in akcje:
        if jest_w_akademiku and akcja.typ_akcji == "wyjscie_z_akademika":
            ok_start = max(start_okna, najwczesniej)
            ok_end = min(akcja.minuta, najpozniej)
            if ok_end > ok_start:
                wynik.append((ok_start, ok_end))
            jest_w_akademiku = False

        elif not jest_w_akademiku and akcja.typ_akcji == "powrot_do_akademika":
            start_okna = akcja.minuta
            jest_w_akademiku = True

    if jest_w_akademiku:
        ok_start = max(start_okna, najwczesniej)
        ok_end = najpozniej
        if ok_end > ok_start:
            wynik.append((ok_start, ok_end))

    return wynik


def _akcje_losowe_dnia(
    generator: random.Random,
    akcje_bazowe: list[AkcjaDniaAgenta],
    prawdopodobienstwo_losowego_cyklu_dnia: float,
    minimalna_liczba_losowych_cykli: int,
    maksymalna_liczba_losowych_cykli: int,
    min_czas_poza_akademikiem_minuty: int,
    max_czas_poza_akademikiem_minuty: int,
    najwczesniejsza_minuta_losowych_akcji: int,
    najpozniejsza_minuta_losowych_akcji: int,
    minimalny_odstep_od_innych_akcji_minuty: int,
) -> list[AkcjaDniaAgenta]:
    los = generator.random()
    if los > prawdopodobienstwo_losowego_cyklu_dnia:
        return []

    okna = _okna_pobytu_w_akademiku(
        akcje_bazowe=akcje_bazowe,
        najwczesniej=najwczesniejsza_minuta_losowych_akcji,
        najpozniej=najpozniejsza_minuta_losowych_akcji,
    )
    if not okna:
        return []

    liczba_cykli = generator.randint(minimalna_liczba_losowych_cykli, maksymalna_liczba_losowych_cykli)
    generator.shuffle(okna)

    wynik: list[AkcjaDniaAgenta] = []
    wykorzystane_okna = 0

    for okno_start, okno_end in okna:
        if wykorzystane_okna >= liczba_cykli:
            break

        maks_czas_pozostania = min(max_czas_poza_akademikiem_minuty, okno_end - okno_start - 2 * minimalny_odstep_od_innych_akcji_minuty)
        if maks_czas_pozostania < min_czas_poza_akademikiem_minuty:
            continue

        czas_poza = generator.randint(min_czas_poza_akademikiem_minuty, maks_czas_pozostania)
        najpozniejsze_wyjscie = okno_end - czas_poza - minimalny_odstep_od_innych_akcji_minuty
        najwczesniejsze_wyjscie = okno_start + minimalny_odstep_od_innych_akcji_minuty

        if najpozniejsze_wyjscie <= najwczesniejsze_wyjscie:
            continue

        minuta_wyjscia = generator.randint(najwczesniejsze_wyjscie, najpozniejsze_wyjscie)
        minuta_powrotu = minuta_wyjscia + czas_poza

        wynik.append(
            AkcjaDniaAgenta(
                minuta=minuta_wyjscia,
                typ_akcji="wyjscie_z_akademika",
                opis="Losowe wyjście z akademika",
                czy_losowe=True,
            )
        )
        wynik.append(
            AkcjaDniaAgenta(
                minuta=minuta_powrotu,
                typ_akcji="powrot_do_akademika",
                opis="Losowy powrót do akademika",
                czy_losowe=True,
            )
        )
        wykorzystane_okna += 1

    return wynik


def zbuduj_harmonogram_przejazdow_agenta(
    plan: PlanZajec,
    dzien: str,
    generator: random.Random,
    bufor_wyjscia_przed_zajeciami_minuty: int = 15,
    prog_powrotu_do_akademika_minuty: int = 120,
    prawdopodobienstwo_losowego_cyklu_dnia: float = 0.25,
    minimalna_liczba_losowych_cykli: int = 1,
    maksymalna_liczba_losowych_cykli: int = 2,
    min_czas_poza_akademikiem_minuty: int = 30,
    max_czas_poza_akademikiem_minuty: int = 120,
    najwczesniejsza_minuta_losowych_akcji: int = 8 * 60,
    najpozniejsza_minuta_losowych_akcji: int = 22 * 60,
    minimalny_odstep_od_innych_akcji_minuty: int = 20,
) -> tuple[list[DecyzjaBlokuDnia], list[AkcjaDniaAgenta]]:
    decyzje = zbuduj_plan_dnia_agenta(plan, dzien, generator)
    bloki_realne = [d for d in decyzje if d.czy_agent_idzie]

    akcje_bazowe: list[AkcjaDniaAgenta] = []
    if bloki_realne:
        pierwszy = bloki_realne[0]
        akcje_bazowe.append(
            AkcjaDniaAgenta(
                minuta=max(0, pierwszy.blok.minuta_startu - bufor_wyjscia_przed_zajeciami_minuty),
                typ_akcji="wyjscie_z_akademika",
                opis=f"Wyjście na blok: {pierwszy.blok.nazwa}",
                czy_losowe=False,
            )
        )

        for obecny, nastepny in zip(bloki_realne, bloki_realne[1:]):
            przerwa = policz_przerwe_miedzy_blokami(obecny.blok, nastepny.blok)
            if czy_przerwa_pozwala_na_powrot(przerwa, prog_minut=prog_powrotu_do_akademika_minuty):
                akcje_bazowe.append(
                    AkcjaDniaAgenta(
                        minuta=obecny.blok.minuta_konca,
                        typ_akcji="powrot_do_akademika",
                        opis=f"Powrót po bloku: {obecny.blok.nazwa}",
                        czy_losowe=False,
                    )
                )
                akcje_bazowe.append(
                    AkcjaDniaAgenta(
                        minuta=max(0, nastepny.blok.minuta_startu - bufor_wyjscia_przed_zajeciami_minuty),
                        typ_akcji="wyjscie_z_akademika",
                        opis=f"Wyjście na blok: {nastepny.blok.nazwa}",
                        czy_losowe=False,
                    )
                )

        ostatni = bloki_realne[-1]
        akcje_bazowe.append(
            AkcjaDniaAgenta(
                minuta=ostatni.blok.minuta_konca,
                typ_akcji="powrot_do_akademika",
                opis=f"Powrót po ostatnim bloku: {ostatni.blok.nazwa}",
                czy_losowe=False,
            )
        )

    akcje_losowe = _akcje_losowe_dnia(
        generator=generator,
        akcje_bazowe=akcje_bazowe,
        prawdopodobienstwo_losowego_cyklu_dnia=prawdopodobienstwo_losowego_cyklu_dnia,
        minimalna_liczba_losowych_cykli=minimalna_liczba_losowych_cykli,
        maksymalna_liczba_losowych_cykli=maksymalna_liczba_losowych_cykli,
        min_czas_poza_akademikiem_minuty=min_czas_poza_akademikiem_minuty,
        max_czas_poza_akademikiem_minuty=max_czas_poza_akademikiem_minuty,
        najwczesniejsza_minuta_losowych_akcji=najwczesniejsza_minuta_losowych_akcji,
        najpozniejsza_minuta_losowych_akcji=najpozniejsza_minuta_losowych_akcji,
        minimalny_odstep_od_innych_akcji_minuty=minimalny_odstep_od_innych_akcji_minuty,
    )

    akcje = sorted(akcje_bazowe + akcje_losowe, key=lambda a: (a.minuta, a.typ_akcji, a.czy_losowe))
    return decyzje, akcje
