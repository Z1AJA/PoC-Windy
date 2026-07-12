from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class LoggerSymulacji:
    katalog_wyjscia: Path
    probki_czasowe: list[dict] = field(default_factory=list)
    zdarzenia: list[dict] = field(default_factory=list)
    _licznik_zdarzen_przeczytanych: int = 0

    def __post_init__(self) -> None:
        self.katalog_wyjscia.mkdir(parents=True, exist_ok=True)

    def zapisz_probke(
        self,
        czas_info: dict,
        snapshot_windy: dict,
        snapshot_menedzera: dict,
        snapshot_energii: dict | None = None,
    ) -> None:
        rekord = {
            "czas": dict(czas_info),
            "winda": dict(snapshot_windy),
            "stany_agentow": dict(snapshot_menedzera["stany_agentow"]),
            "statystyki": dict(snapshot_menedzera["statystyki"]),
            "kolejki": dict(snapshot_menedzera["kolejki"]),
            "metryki_zbiorcze": dict(snapshot_menedzera["metryki_zbiorcze"]),
        }
        if snapshot_energii is not None:
            rekord["energia"] = dict(snapshot_energii)
        self.probki_czasowe.append(rekord)

    def pobierz_nowe_zdarzenia_z_menedzera(self, menedzer) -> None:
        wszystkie = list(menedzer.log_zdarzen)
        nowe = wszystkie[self._licznik_zdarzen_przeczytanych:]
        self.zdarzenia.extend(nowe)
        self._licznik_zdarzen_przeczytanych = len(wszystkie)

    def eksportuj_plany_dnia_json(self, menedzer, nazwa_pliku: str = "plany_dnia_agentow.json") -> Path:
        dane = menedzer.plan_dnia_agentow()
        sciezka = self.katalog_wyjscia / nazwa_pliku
        sciezka.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
        return sciezka

    def eksportuj_plany_dnia_txt(self, menedzer, nazwa_pliku: str = "plany_dnia_agentow.txt") -> Path:
        dane = menedzer.plan_dnia_agentow()
        linie = []
        for agent_id in sorted(dane.keys()):
            agent = dane[agent_id]
            linie.append(f"=== {agent_id} ===")
            linie.append(f"dzien: {agent.get('dzien_planu')}")
            linie.append("decyzje_dnia:")
            for decyzja in agent.get("decyzje_dnia", []):
                status = "IDZIE" if decyzja["czy_agent_idzie"] else "NIE IDZIE"
                linie.append(
                    f"  - {decyzja['godzina_od']}-{decyzja['godzina_do']} | "
                    f"{decyzja['nazwa']} | {status} | {decyzja['powod']}"
                )
            linie.append("harmonogram_dnia:")
            for akcja in agent.get("harmonogram_dnia", []):
                znacznik = " [LOSOWE]" if akcja.get("czy_losowe") else ""
                start = akcja.get("pietro_startowe_symulowane")
                cel = akcja.get("pietro_docelowe")
                trasa = f" | P{start} -> P{cel}" if start is not None and cel is not None else ""
                etykieta = akcja.get("etykieta", akcja["typ_akcji"])
                linie.append(
                    f"  - {akcja['czas']} | {etykieta}{trasa} | {akcja['opis']}{znacznik}"
                )
            linie.append("")
        sciezka = self.katalog_wyjscia / nazwa_pliku
        sciezka.write_text("\n".join(linie), encoding="utf-8")
        return sciezka

    def eksportuj_probki_jsonl(self, nazwa_pliku: str = "probki_czasowe.jsonl") -> Path:
        sciezka = self.katalog_wyjscia / nazwa_pliku
        with sciezka.open("w", encoding="utf-8") as f:
            for rekord in self.probki_czasowe:
                f.write(json.dumps(rekord, ensure_ascii=False) + "\n")
        return sciezka

    def eksportuj_zdarzenia_jsonl(self, nazwa_pliku: str = "zdarzenia_symulacji.jsonl") -> Path:
        sciezka = self.katalog_wyjscia / nazwa_pliku
        with sciezka.open("w", encoding="utf-8") as f:
            for rekord in self.zdarzenia:
                f.write(json.dumps(rekord, ensure_ascii=False) + "\n")
        return sciezka
