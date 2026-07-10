from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RekordObserwowalnyML:
    tick: int
    nazwa_dnia: str
    czas_tekst: str
    typ_nacisniecia: str
    pietro: int
    kierunek: str
    obciazenie_windy: int

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "nazwa_dnia": self.nazwa_dnia,
            "czas_tekst": self.czas_tekst,
            "typ_nacisniecia": self.typ_nacisniecia,
            "pietro": self.pietro,
            "kierunek": self.kierunek,
            "obciazenie_windy": self.obciazenie_windy,
        }


@dataclass(slots=True)
class RejestratorObserwacjiML:
    rekordy: list[RekordObserwowalnyML] = field(default_factory=list)

    def zarejestruj_wezwanie_z_pietra(
        self,
        *,
        tick: int,
        nazwa_dnia: str,
        czas_tekst: str,
        pietro: int,
        kierunek: str,
        obciazenie_windy: int,
    ) -> None:
        self.rekordy.append(
            RekordObserwowalnyML(
                tick=tick,
                nazwa_dnia=nazwa_dnia,
                czas_tekst=czas_tekst,
                typ_nacisniecia="wezwanie_z_pietra",
                pietro=pietro,
                kierunek=kierunek,
                obciazenie_windy=obciazenie_windy,
            )
        )

    def zarejestruj_wybor_z_kabiny(
        self,
        *,
        tick: int,
        nazwa_dnia: str,
        czas_tekst: str,
        pietro_docelowe: int,
        kierunek: str,
        obciazenie_windy: int,
    ) -> None:
        self.rekordy.append(
            RekordObserwowalnyML(
                tick=tick,
                nazwa_dnia=nazwa_dnia,
                czas_tekst=czas_tekst,
                typ_nacisniecia="wybor_z_kabiny",
                pietro=pietro_docelowe,
                kierunek=kierunek,
                obciazenie_windy=obciazenie_windy,
            )
        )

    def liczba_rekordow(self) -> int:
        return len(self.rekordy)

    def rekordy_jako_dict(self) -> list[dict]:
        return [rekord.to_dict() for rekord in self.rekordy]
