from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ParametryEnergetyczne:
    energia_rozruchu: float = 1.2
    energia_bazowa_na_pietro: float = 0.8
    energia_na_osobe_na_pietro: float = 0.12
    energia_postoju_na_tick: float = 0.02
    mnoznik_jazdy_w_dol: float = 0.85

    def __post_init__(self) -> None:
        for nazwa in [
            "energia_rozruchu",
            "energia_bazowa_na_pietro",
            "energia_na_osobe_na_pietro",
            "energia_postoju_na_tick",
            "mnoznik_jazdy_w_dol",
        ]:
            wartosc = getattr(self, nazwa)
            if wartosc < 0:
                raise ValueError(f"{nazwa} nie może być ujemne")


class MonitorEnergiiWindy:
    def __init__(self, parametry: ParametryEnergetyczne | None = None) -> None:
        self.parametry = parametry or ParametryEnergetyczne()
        self._poprzedni_snapshot: dict | None = None

        self.energia_calkowita = 0.0
        self.energia_rozruchow = 0.0
        self.energia_jazdy = 0.0
        self.energia_postoju = 0.0

        self.liczba_rozruchow = 0
        self.liczba_przejazdow_miedzy_pietrami = 0
        self.liczba_tickow_postoju = 0

    def krok(self, snapshot_windy: dict) -> None:
        if self._poprzedni_snapshot is None:
            self._poprzedni_snapshot = dict(snapshot_windy)
            return

        poprzedni = self._poprzedni_snapshot
        obecny = snapshot_windy

        # rozruch
        if obecny["czy_jedzie"] and not poprzedni["czy_jedzie"]:
            self.energia_calkowita += self.parametry.energia_rozruchu
            self.energia_rozruchow += self.parametry.energia_rozruchu
            self.liczba_rozruchow += 1

        # przejazd między piętrami
        roznica_pieter = abs(int(obecny["aktualne_pietro"]) - int(poprzedni["aktualne_pietro"]))
        if roznica_pieter > 0:
            obciazenie = int(poprzedni.get("obciazenie", 0))
            energia_podstawowa = roznica_pieter * (
                self.parametry.energia_bazowa_na_pietro +
                self.parametry.energia_na_osobe_na_pietro * obciazenie
            )

            if obecny.get("kierunek") == "DOL":
                energia_podstawowa *= self.parametry.mnoznik_jazdy_w_dol

            self.energia_calkowita += energia_podstawowa
            self.energia_jazdy += energia_podstawowa
            self.liczba_przejazdow_miedzy_pietrami += roznica_pieter

        # postój
        if obecny.get("czy_stoi_na_przystanku", False):
            self.energia_calkowita += self.parametry.energia_postoju_na_tick
            self.energia_postoju += self.parametry.energia_postoju_na_tick
            self.liczba_tickow_postoju += 1

        self._poprzedni_snapshot = dict(snapshot_windy)

    def snapshot(self) -> dict:
        return {
            "energia_calkowita": round(self.energia_calkowita, 4),
            "energia_rozruchow": round(self.energia_rozruchow, 4),
            "energia_jazdy": round(self.energia_jazdy, 4),
            "energia_postoju": round(self.energia_postoju, 4),
            "liczba_rozruchow": self.liczba_rozruchow,
            "liczba_przejazdow_miedzy_pietrami": self.liczba_przejazdow_miedzy_pietrami,
            "liczba_tickow_postoju": self.liczba_tickow_postoju,
        }
