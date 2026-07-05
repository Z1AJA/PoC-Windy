from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto

from Modele_planow import PlanZajec
from Nawigacja_po_planie import AkcjaDniaAgenta, DecyzjaBlokuDnia, zbuduj_harmonogram_przejazdow_agenta
from Ustawienia_projektu import UstawieniaProjektu


class StanAgenta(Enum):
    W_AKADEMIKU = auto()
    POZA_AKADEMIKIEM = auto()
    CZEKA_NA_WINDE_W_DOL = auto()
    CZEKA_NA_WINDE_W_GORE = auto()
    JEDZIE_WINDA = auto()
    IDZIE_SCHODAMI_W_DOL = auto()
    IDZIE_SCHODAMI_W_GORE = auto()


@dataclass(slots=True)
class AgentStudenta:
    id_agenta: str
    pietro_domowe: int
    plan: PlanZajec
    ustawienia: UstawieniaProjektu
    seed_agenta: int

    stan: StanAgenta = StanAgenta.W_AKADEMIKU
    aktualne_pietro: int | None = None
    cel_pietro: int | None = None

    dzien_planu: str | None = None
    decyzje_dnia: list[DecyzjaBlokuDnia] = field(default_factory=list)
    harmonogram_dnia: list[AkcjaDniaAgenta] = field(default_factory=list)
    indeks_nastepnej_akcji: int = 0

    pozycja_w_kolejce: int | None = None
    kierunek_kolejki: str | None = None
    tick_wejscia_do_kolejki: int | None = None

    liczba_ghost_calli: int = 0
    liczba_rezygnacji_na_schody: int = 0

    _generator: random.Random = field(init=False, repr=False)
    _aktualny_tick_pomocniczy: int = field(default=0, init=False, repr=False)
    log_zdarzen: list[dict] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.pietro_domowe < 0:
            raise ValueError("pietro_domowe nie może być ujemne")

        if self.aktualne_pietro is None:
            self.aktualne_pietro = self.pietro_domowe

        self._generator = random.Random(self.seed_agenta)
        self._zaloguj("inicjalizacja", {
            "pietro_domowe": self.pietro_domowe,
            "seed_agenta": self.seed_agenta,
        })

    @property
    def czy_jest_w_akademiku(self) -> bool:
        return self.stan != StanAgenta.POZA_AKADEMIKIEM

    @property
    def czy_czeka_w_kolejce(self) -> bool:
        return self.pozycja_w_kolejce is not None

    @property
    def ticki_oczekiwania_w_kolejce(self) -> int:
        if self.tick_wejscia_do_kolejki is None:
            return 0
        return max(0, self._aktualny_tick_pomocniczy - self.tick_wejscia_do_kolejki)

    def przygotuj_dzien(self, dzien: str) -> None:
        self.dzien_planu = dzien
        self.decyzje_dnia, self.harmonogram_dnia = zbuduj_harmonogram_przejazdow_agenta(
            self.plan,
            dzien,
            self._generator,
            bufor_wyjscia_przed_zajeciami_minuty=self.ustawienia.bufor_wyjscia_przed_zajeciami_minuty,
            prog_powrotu_do_akademika_minuty=self.ustawienia.prog_powrotu_do_akademika_minuty,
        )
        self.indeks_nastepnej_akcji = 0
        self._zaloguj("przygotowano_dzien", {
            "dzien": dzien,
            "liczba_blokow": len(self.decyzje_dnia),
            "liczba_akcji": len(self.harmonogram_dnia),
        })

    def pobierz_akcje_do_wykonania(self, minuta_dnia: int) -> list[AkcjaDniaAgenta]:
        akcje = []
        while self.indeks_nastepnej_akcji < len(self.harmonogram_dnia):
            akcja = self.harmonogram_dnia[self.indeks_nastepnej_akcji]
            if akcja.minuta > minuta_dnia:
                break
            akcje.append(akcja)
            self.indeks_nastepnej_akcji += 1
        return akcje

    def dolacz_do_kolejki(
        self,
        kierunek: str,
        tick: int,
        pozycja: int,
        cel_pietro: int,
    ) -> None:
        if kierunek not in {"dol", "gora"}:
            raise ValueError("kierunek musi być równy 'dol' albo 'gora'")

        self.pozycja_w_kolejce = pozycja
        self.kierunek_kolejki = kierunek
        self.tick_wejscia_do_kolejki = tick
        self.cel_pietro = cel_pietro

        if kierunek == "dol":
            self.stan = StanAgenta.CZEKA_NA_WINDE_W_DOL
        else:
            self.stan = StanAgenta.CZEKA_NA_WINDE_W_GORE

        self._zaloguj("dolaczono_do_kolejki", {
            "kierunek": kierunek,
            "tick": tick,
            "pozycja": pozycja,
            "cel_pietro": cel_pietro,
        })

    def zaktualizuj_pozycje_w_kolejce(self, pozycja: int | None) -> None:
        self.pozycja_w_kolejce = pozycja
        self._zaloguj("aktualizacja_pozycji_w_kolejce", {"pozycja": pozycja})

    def opusc_kolejke(self) -> None:
        self._zaloguj("opuszczono_kolejke", {
            "pozycja": self.pozycja_w_kolejce,
            "kierunek": self.kierunek_kolejki,
        })
        self.pozycja_w_kolejce = None
        self.kierunek_kolejki = None
        self.tick_wejscia_do_kolejki = None

    def czy_rezygnuje_i_idzie_schodami(self, aktualny_tick: int) -> bool:
        if not self.czy_czeka_w_kolejce:
            return False
        if self.kierunek_kolejki is None:
            return False

        self._aktualny_tick_pomocniczy = aktualny_tick
        ticki_czekania = self.ticki_oczekiwania_w_kolejce

        prawdopodobienstwo = self.ustawienia.prawdopodobienstwo_rezygnacji_schodami(
            pietro=self.aktualne_pietro or self.pietro_domowe,
            kierunek=self.kierunek_kolejki,
            ticki_czekania=ticki_czekania,
        )
        los = self._generator.random()

        if los <= prawdopodobienstwo:
            kierunek = self.kierunek_kolejki
            self.liczba_ghost_calli += 1
            self.liczba_rezygnacji_na_schody += 1
            self.opusc_kolejke()

            if kierunek == "dol":
                self.stan = StanAgenta.IDZIE_SCHODAMI_W_DOL
            else:
                self.stan = StanAgenta.IDZIE_SCHODAMI_W_GORE

            self._zaloguj("rezygnacja_na_schody", {
                "tick": aktualny_tick,
                "los": round(los, 6),
                "prawdopodobienstwo": round(prawdopodobienstwo, 6),
                "kierunek": kierunek,
            })
            return True

        return False

    def zakoncz_przejscie_schodami(self) -> None:
        if self.stan == StanAgenta.IDZIE_SCHODAMI_W_DOL:
            self.aktualne_pietro = self.ustawienia.pietro_parteru
            self.stan = StanAgenta.POZA_AKADEMIKIEM
        elif self.stan == StanAgenta.IDZIE_SCHODAMI_W_GORE:
            self.aktualne_pietro = self.pietro_domowe
            self.stan = StanAgenta.W_AKADEMIKU
        self._zaloguj("zakonczono_schody", {
            "stan_po": self.stan.name,
            "aktualne_pietro": self.aktualne_pietro,
        })

    def rozpocznij_przejazd_winda(self) -> None:
        self.stan = StanAgenta.JEDZIE_WINDA
        self._zaloguj("rozpoczecie_przejazdu_winda", {
            "cel_pietro": self.cel_pietro,
        })

    def zakoncz_przejazd(self, pietro_docelowe: int) -> None:
        self.aktualne_pietro = pietro_docelowe
        self.cel_pietro = None
        self.opusc_kolejke()

        if pietro_docelowe == self.ustawienia.pietro_parteru:
            self.stan = StanAgenta.POZA_AKADEMIKIEM
        elif pietro_docelowe == self.pietro_domowe:
            self.stan = StanAgenta.W_AKADEMIKU
        else:
            self.stan = StanAgenta.W_AKADEMIKU

        self._zaloguj("zakonczenie_przejazdu", {
            "pietro_docelowe": pietro_docelowe,
            "stan_po": self.stan.name,
        })

    def snapshot(self) -> dict:
        return {
            "id_agenta": self.id_agenta,
            "pietro_domowe": self.pietro_domowe,
            "aktualne_pietro": self.aktualne_pietro,
            "stan": self.stan.name,
            "czy_jest_w_akademiku": self.czy_jest_w_akademiku,
            "pozycja_w_kolejce": self.pozycja_w_kolejce,
            "kierunek_kolejki": self.kierunek_kolejki,
            "tick_wejscia_do_kolejki": self.tick_wejscia_do_kolejki,
            "cel_pietro": self.cel_pietro,
            "liczba_ghost_calli": self.liczba_ghost_calli,
            "liczba_rezygnacji_na_schody": self.liczba_rezygnacji_na_schody,
            "dzien_planu": self.dzien_planu,
            "liczba_blokow_w_dniu": len(self.decyzje_dnia),
            "liczba_akcji_w_dniu": len(self.harmonogram_dnia),
        }

    def _zaloguj(self, typ: str, payload: dict) -> None:
        self.log_zdarzen.append({
            "typ": typ,
            "payload": payload,
        })
