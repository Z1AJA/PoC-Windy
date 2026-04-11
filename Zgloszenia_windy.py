from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple
import itertools

from Kierunki_i_typy import Kierunek, ZrodloZgloszenia, TypZgloszenia


_licznik_id_zgloszen = itertools.count(1)


@dataclass(slots=True)
class ZgloszenieWindy:
    typ_zgloszenia: TypZgloszenia
    zrodlo: ZrodloZgloszenia
    tick_utworzenia: int
    pietro: int
    kierunek: Optional[Kierunek] = None
    pietro_docelowe: Optional[int] = None
    id_zgloszenia: int = field(default_factory=lambda: next(_licznik_id_zgloszen))

    def __post_init__(self) -> None:
        if self.typ_zgloszenia == TypZgloszenia.WEZWANIE_Z_PIETRA:
            if self.kierunek not in (Kierunek.GORA, Kierunek.DOL):
                raise ValueError("WEZWANIE_Z_PIETRA wymaga kierunku GORA albo DOL")
            if self.pietro_docelowe is not None:
                raise ValueError("WEZWANIE_Z_PIETRA nie może mieć pietro_docelowe")
        elif self.typ_zgloszenia == TypZgloszenia.WYBOR_Z_KABINY:
            if self.pietro_docelowe is None:
                raise ValueError("WYBOR_Z_KABINY wymaga pietro_docelowe")
            if self.kierunek is not None:
                raise ValueError("WYBOR_Z_KABINY nie może mieć kierunku")
        else:
            raise ValueError("Nieznany typ_zgloszenia")

    @property
    def klucz_deduplicacji(self) -> Tuple:
        if self.typ_zgloszenia == TypZgloszenia.WEZWANIE_Z_PIETRA:
            return ("WEZWANIE", self.pietro, self.kierunek)
        return ("KABINA", self.pietro_docelowe)
