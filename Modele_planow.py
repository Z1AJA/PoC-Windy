from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


KOLEJNOSC_DNI = [
    "poniedzialek",
    "wtorek",
    "sroda",
    "czwartek",
    "piatek",
    "sobota",
    "niedziela",
]


def czas_hhmm_na_minuty(wartosc: str) -> int:
    if not isinstance(wartosc, str) or ":" not in wartosc:
        raise ValueError(f"Niepoprawny format czasu: {wartosc!r}")

    godzina_txt, minuta_txt = wartosc.split(":", 1)
    godzina = int(godzina_txt)
    minuta = int(minuta_txt)

    if not (0 <= godzina <= 23):
        raise ValueError(f"Godzina poza zakresem: {wartosc!r}")
    if not (0 <= minuta <= 59):
        raise ValueError(f"Minuta poza zakresem: {wartosc!r}")

    return godzina * 60 + minuta


def czas_minuty_na_hhmm(liczba_minut: int) -> str:
    if liczba_minut < 0:
        raise ValueError("liczba_minut nie może być ujemna")

    godzina = liczba_minut // 60
    minuta = liczba_minut % 60

    if godzina > 23:
        raise ValueError("czas wykracza poza pojedynczą dobę")

    return f"{godzina:02d}:{minuta:02d}"


@dataclass(frozen=True, slots=True)
class BlokZajec:
    godzina_od: str
    godzina_do: str
    nazwa: str
    wspolczynnik_uczestnictwa: float

    def __post_init__(self) -> None:
        start = czas_hhmm_na_minuty(self.godzina_od)
        koniec = czas_hhmm_na_minuty(self.godzina_do)

        if koniec <= start:
            raise ValueError(
                f"Blok {self.nazwa!r} ma niepoprawny zakres czasu: "
                f"{self.godzina_od} -> {self.godzina_do}"
            )

        if not (0.0 <= self.wspolczynnik_uczestnictwa <= 1.0):
            raise ValueError(
                f"wspolczynnik_uczestnictwa poza zakresem 0..1 dla bloku {self.nazwa!r}"
            )

    @property
    def minuta_startu(self) -> int:
        return czas_hhmm_na_minuty(self.godzina_od)

    @property
    def minuta_konca(self) -> int:
        return czas_hhmm_na_minuty(self.godzina_do)

    @property
    def czas_trwania_minuty(self) -> int:
        return self.minuta_konca - self.minuta_startu

    @property
    def czy_obowiazkowe(self) -> bool:
        return self.wspolczynnik_uczestnictwa >= 1.0

    def to_dict(self) -> dict:
        return {
            "godzina_od": self.godzina_od,
            "godzina_do": self.godzina_do,
            "nazwa": self.nazwa,
            "wspolczynnik_uczestnictwa": self.wspolczynnik_uczestnictwa,
        }


@dataclass(frozen=True, slots=True)
class DzienPlanu:
    dzien: str
    bloki: tuple[BlokZajec, ...]

    def __post_init__(self) -> None:
        if self.dzien not in KOLEJNOSC_DNI:
            raise ValueError(f"Nieznany dzien tygodnia: {self.dzien!r}")

    @property
    def czy_sa_zajecia(self) -> bool:
        return len(self.bloki) > 0

    @property
    def pierwszy_blok(self) -> BlokZajec | None:
        return self.bloki[0] if self.bloki else None

    @property
    def ostatni_blok(self) -> BlokZajec | None:
        return self.bloki[-1] if self.bloki else None

    def to_dict(self) -> dict:
        return {
            "dzien": self.dzien,
            "czy_sa_zajecia": self.czy_sa_zajecia,
            "bloki": [blok.to_dict() for blok in self.bloki],
        }


@dataclass(frozen=True, slots=True)
class PlanZajec:
    plan_id: str
    rok: int
    grupa: int
    wariant_zrodlowy: str
    dni: tuple[DzienPlanu, ...]

    def __post_init__(self) -> None:
        dni_posortowane = sorted(self.dni, key=lambda dz: KOLEJNOSC_DNI.index(dz.dzien))
        object.__setattr__(self, "dni", tuple(dni_posortowane))

    def dzien(self, nazwa_dnia: str) -> DzienPlanu | None:
        for dz in self.dni:
            if dz.dzien == nazwa_dnia:
                return dz
        return None

    def iter_bloki(self) -> Iterable[tuple[str, BlokZajec]]:
        for dz in self.dni:
            for blok in dz.bloki:
                yield dz.dzien, blok

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "rok": self.rok,
            "grupa": self.grupa,
            "wariant_zrodlowy": self.wariant_zrodlowy,
            "dni": [dzien.to_dict() for dzien in self.dni],
        }

    def opis_skrocony(self) -> str:
        liczba_blokow = sum(len(dzien.bloki) for dzien in self.dni)
        return (
            f"{self.plan_id} | rok={self.rok} | grupa={self.grupa} | "
            f"wariant={self.wariant_zrodlowy} | bloki={liczba_blokow}"
        )
