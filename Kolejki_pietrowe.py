from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class KolejkiPietrowe:
    kolejki: dict[int, dict[str, list[str]]] = field(default_factory=dict)

    def _upewnij_pietro(self, pietro: int) -> None:
        if pietro not in self.kolejki:
            self.kolejki[pietro] = {"gora": [], "dol": []}

    def dolacz(self, id_agenta: str, pietro: int, kierunek: str) -> int:
        if kierunek not in {"gora", "dol"}:
            raise ValueError("kierunek musi być równy 'gora' albo 'dol'")

        self._upewnij_pietro(pietro)
        kolejka = self.kolejki[pietro][kierunek]

        if id_agenta in kolejka:
            return kolejka.index(id_agenta) + 1

        kolejka.append(id_agenta)
        return len(kolejka)

    def usun(self, id_agenta: str, pietro: int, kierunek: str) -> None:
        self._upewnij_pietro(pietro)
        kolejka = self.kolejki[pietro][kierunek]
        if id_agenta in kolejka:
            kolejka.remove(id_agenta)

    def pobierz_pozycje(self, id_agenta: str, pietro: int, kierunek: str) -> int | None:
        self._upewnij_pietro(pietro)
        kolejka = self.kolejki[pietro][kierunek]
        if id_agenta not in kolejka:
            return None
        return kolejka.index(id_agenta) + 1

    def pobierz_pierwszych(self, pietro: int, kierunek: str, ile: int) -> list[str]:
        self._upewnij_pietro(pietro)
        return list(self.kolejki[pietro][kierunek][:ile])

    def liczba_oczekujacych(self, pietro: int, kierunek: str) -> int:
        self._upewnij_pietro(pietro)
        return len(self.kolejki[pietro][kierunek])

    def snapshot(self) -> dict:
        wynik = {}
        for pietro in sorted(self.kolejki.keys()):
            wynik[pietro] = {
                "gora": list(self.kolejki[pietro]["gora"]),
                "dol": list(self.kolejki[pietro]["dol"]),
            }
        return wynik
