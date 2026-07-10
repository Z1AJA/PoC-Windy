from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

from Agent_studenta import AgentStudenta, StanAgenta
from Kolejki_pietrowe import KolejkiPietrowe
from Loader_planow import RepozytoriumPlanow
from Rejestrator_ml import RejestratorObserwacjiML
from Silnik_windy import SilnikWindy
from Kierunki_i_typy import Kierunek, ZrodloZgloszenia
from Ustawienia_projektu import UstawieniaProjektu


@dataclass(frozen=True, slots=True)
class KonfiguracjaGrupyAgentow:
    nazwa: str
    plan_id: str
    pietro_domowe: int
    liczba_agentow: int


class MenedzerAgentow:
    def __init__(
        self,
        repozytorium_planow: RepozytoriumPlanow,
        silnik_windy: SilnikWindy,
        ustawienia: UstawieniaProjektu,
    ) -> None:
        self.repozytorium_planow = repozytorium_planow
        self.silnik_windy = silnik_windy
        self.ustawienia = ustawienia

        self.agenci: dict[str, AgentStudenta] = {}
        self.kolejki = KolejkiPietrowe()
        self.agenci_w_windzie: list[str] = []
        self.rejestrator_ml = RejestratorObserwacjiML()

        self._generator_glowny = random.Random(self.ustawienia.seed_glowny)
        self._dzien_aktywny: str | None = None
        self._tick_ostatniej_obslugi_przystanku: int | None = None
        self._ostatni_tick_kroku: int = 0
        self._ostatni_czas_info: dict | None = None

        self.log_zdarzen = deque(maxlen=5000)
        self.statystyki = {
            "liczba_nacisniec_agentowych": 0,
            "liczba_wejsc_do_windy": 0,
            "liczba_wyjsc_z_windy": 0,
            "liczba_rezygnacji_schody": 0,
            "liczba_ghost_calli": 0,
        }

    def dodaj_grupe(self, konfiguracja: KonfiguracjaGrupyAgentow) -> None:
        plan = self.repozytorium_planow.pobierz(konfiguracja.plan_id)
        for indeks in range(konfiguracja.liczba_agentow):
            agent_id = f"{konfiguracja.nazwa}_{indeks + 1:03d}"
            self.agenci[agent_id] = AgentStudenta(
                id_agenta=agent_id,
                pietro_domowe=konfiguracja.pietro_domowe,
                plan=plan,
                ustawienia=self.ustawienia,
                seed_agenta=self._generator_glowny.randint(1, 10_000_000),
            )

        self._zaloguj(
            "dodano_grupe",
            {
                "nazwa": konfiguracja.nazwa,
                "plan_id": konfiguracja.plan_id,
                "pietro_domowe": konfiguracja.pietro_domowe,
                "liczba_agentow": konfiguracja.liczba_agentow,
            },
        )

    def przygotuj_dzien(self, nazwa_dnia: str) -> None:
        self._dzien_aktywny = nazwa_dnia
        for agent in self.agenci.values():
            agent.przygotuj_dzien(nazwa_dnia)
        self._zaloguj("przygotowano_dzien", {"dzien": nazwa_dnia})

    def plan_dnia_agentow(self) -> dict:
        return {
            agent_id: agent.serializuj_plan_dnia()
            for agent_id, agent in sorted(self.agenci.items())
        }

    def metryki_agentow(self) -> dict:
        return {
            agent_id: {
                "statystyki": agent.statystyki_przejazdow(),
                "historia_przejazdow": list(agent.historia_przejazdow),
            }
            for agent_id, agent in sorted(self.agenci.items())
        }

    def rekordy_ml_obserwowalne(self) -> list[dict]:
        return self.rejestrator_ml.rekordy_jako_dict()

    def _agreguj_metryki(self) -> dict:
        rekordy = []
        for agent in self.agenci.values():
            rekordy.extend([r for r in agent.historia_przejazdow if r["typ_zakonczenia"] == "winda"])

        def srednia(pole: str):
            wartosci = [r[pole] for r in rekordy if r.get(pole) is not None]
            if not wartosci:
                return None
            return round(sum(wartosci) / len(wartosci), 3)

        return {
            "liczba_przejazdow_winda": len(rekordy),
            "sredni_czas_oczekiwania_tick": srednia("czas_oczekiwania_tick"),
            "sredni_czas_przejazdu_tick": srednia("czas_przejazdu_tick"),
            "sredni_czas_calkowity_tick": srednia("czas_calkowity_tick"),
        }

    def krok(self, czas_info: dict) -> None:
        self._ostatni_czas_info = dict(czas_info)
        nazwa_dnia = czas_info["nazwa_dnia"]
        minuta_dnia = czas_info["godzina"] * 60 + czas_info["minuta"]
        sekunda = czas_info["sekunda"]
        tick = czas_info["tick"]
        self._ostatni_tick_kroku = tick

        if self._dzien_aktywny != nazwa_dnia:
            self.przygotuj_dzien(nazwa_dnia)

        if sekunda == 0:
            self._obsluz_akcje_z_harmonogramu(minuta_dnia, tick)

        self._obsluz_rezygnacje_na_schody(tick)
        self._obsluz_schody(tick)
        self._obsluz_przystanek_windy(tick)

    def _obsluz_akcje_z_harmonogramu(self, minuta_dnia: int, tick: int) -> None:
        for agent in self.agenci.values():
            if agent.stan in {StanAgenta.CZEKA_NA_WINDE_W_DOL, StanAgenta.CZEKA_NA_WINDE_W_GORE, StanAgenta.JEDZIE_WINDA}:
                continue

            akcje = agent.pobierz_akcje_do_wykonania(minuta_dnia)
            for akcja in akcje:
                if akcja.typ_akcji == "wyjscie_z_akademika" and agent.stan == StanAgenta.W_AKADEMIKU:
                    self._zaloguj("akcja_agenta", {
                        "tick": tick,
                        "agent": agent.id_agenta,
                        "akcja": akcja.typ_akcji,
                        "opis": akcja.opis,
                        "czy_losowe": akcja.czy_losowe,
                    })
                    self._dolacz_agenta_do_kolejki(
                        agent, "dol", tick, self.ustawienia.pietro_parteru,
                        typ_akcji=akcja.typ_akcji, czy_losowe=akcja.czy_losowe,
                    )

                elif akcja.typ_akcji == "powrot_do_akademika" and agent.stan == StanAgenta.POZA_AKADEMIKIEM:
                    agent.aktualne_pietro = self.ustawienia.pietro_parteru
                    self._zaloguj("akcja_agenta", {
                        "tick": tick,
                        "agent": agent.id_agenta,
                        "akcja": akcja.typ_akcji,
                        "opis": akcja.opis,
                        "czy_losowe": akcja.czy_losowe,
                    })
                    self._dolacz_agenta_do_kolejki(
                        agent, "gora", tick, agent.pietro_domowe,
                        typ_akcji=akcja.typ_akcji, czy_losowe=akcja.czy_losowe,
                    )

    def _dolacz_agenta_do_kolejki(self, agent: AgentStudenta, kierunek: str, tick: int, cel_pietro: int, typ_akcji: str | None, czy_losowe: bool) -> None:
        pietro = agent.aktualne_pietro if agent.aktualne_pietro is not None else agent.pietro_domowe
        pozycja = self.kolejki.dolacz(agent.id_agenta, pietro, kierunek)
        agent.dolacz_do_kolejki(
            kierunek=kierunek,
            tick=tick,
            pozycja=pozycja,
            cel_pietro=cel_pietro,
            typ_akcji=typ_akcji,
            czy_losowe=czy_losowe,
        )

        if kierunek == "dol":
            self.silnik_windy.dodaj_wezwanie_z_pietra_teraz(pietro, Kierunek.DOL, ZrodloZgloszenia.CZLOWIEK)
        else:
            self.silnik_windy.dodaj_wezwanie_z_pietra_teraz(pietro, Kierunek.GORA, ZrodloZgloszenia.CZLOWIEK)

        self.statystyki["liczba_nacisniec_agentowych"] += 1
        self._zaloguj("dolaczenie_do_kolejki", {
            "tick": tick,
            "agent": agent.id_agenta,
            "pietro": pietro,
            "kierunek": kierunek,
            "pozycja": pozycja,
            "cel_pietro": cel_pietro,
            "typ_akcji": typ_akcji,
            "czy_losowe": czy_losowe,
            "zrodlo_w_systemie_windy": "CZLOWIEK",
        })
        self._zarejestruj_wezwanie_ml(tick=tick, pietro=pietro, kierunek=kierunek)

    def _zarejestruj_wezwanie_ml(self, tick: int, pietro: int, kierunek: str) -> None:
        if self._ostatni_czas_info is None:
            return
        self.rejestrator_ml.zarejestruj_wezwanie_z_pietra(
            tick=tick,
            nazwa_dnia=self._ostatni_czas_info["nazwa_dnia"],
            czas_tekst=self._ostatni_czas_info["czas_tekst"],
            pietro=pietro,
            kierunek=kierunek,
            obciazenie_windy=self.silnik_windy.obciazenie,
        )

    def _zarejestruj_wybor_kabiny_ml(self, tick: int, pietro_docelowe: int, kierunek: str) -> None:
        if self._ostatni_czas_info is None:
            return
        self.rejestrator_ml.zarejestruj_wybor_z_kabiny(
            tick=tick,
            nazwa_dnia=self._ostatni_czas_info["nazwa_dnia"],
            czas_tekst=self._ostatni_czas_info["czas_tekst"],
            pietro_docelowe=pietro_docelowe,
            kierunek=kierunek,
            obciazenie_windy=self.silnik_windy.obciazenie,
        )

    def _obsluz_rezygnacje_na_schody(self, tick: int) -> None:
        for agent in self.agenci.values():
            if not agent.czy_czeka_w_kolejce:
                continue

            pietro = agent.aktualne_pietro if agent.aktualne_pietro is not None else agent.pietro_domowe
            kierunek = agent.kierunek_kolejki
            if kierunek is None:
                continue

            if agent.czy_rezygnuje_i_idzie_schodami(tick):
                self.kolejki.usun(agent.id_agenta, pietro, kierunek)
                self._przelicz_pozycje_w_kolejce(pietro, kierunek)
                self.statystyki["liczba_rezygnacji_schody"] += 1
                self.statystyki["liczba_ghost_calli"] += 1
                self._zaloguj("rezygnacja_schody", {
                    "tick": tick,
                    "agent": agent.id_agenta,
                    "pietro": pietro,
                    "kierunek": kierunek,
                })

    def _obsluz_schody(self, tick: int) -> None:
        for agent in self.agenci.values():
            if agent.stan in {StanAgenta.IDZIE_SCHODAMI_W_DOL, StanAgenta.IDZIE_SCHODAMI_W_GORE}:
                poprzedni = agent.stan.name
                agent.zakoncz_przejscie_schodami(tick)
                self._zaloguj("zakonczono_schody", {
                    "agent": agent.id_agenta,
                    "stan_przed": poprzedni,
                    "stan_po": agent.stan.name,
                    "pietro": agent.aktualne_pietro,
                    "tick": tick,
                })

    def _obsluz_przystanek_windy(self, tick: int) -> None:
        if not self.silnik_windy.czy_stoi_na_przystanku:
            return

        if self._tick_ostatniej_obslugi_przystanku == tick:
            return

        self._tick_ostatniej_obslugi_przystanku = tick
        pietro = self.silnik_windy.aktualne_pietro

        self._wypusc_agentow_z_windy(pietro, tick)
        self._wpusc_agentow_do_windy(pietro, tick)

    def _wypusc_agentow_z_windy(self, pietro: int, tick: int) -> None:
        do_wypuszczenia = []
        for agent_id in self.agenci_w_windzie:
            agent = self.agenci[agent_id]
            if agent.cel_pietro == pietro:
                do_wypuszczenia.append(agent_id)

        for agent_id in do_wypuszczenia:
            agent = self.agenci[agent_id]
            agent.zakoncz_przejazd(pietro, tick)
            while agent_id in self.agenci_w_windzie:
                self.agenci_w_windzie.remove(agent_id)
                self.silnik_windy.obciazenie = max(0, self.silnik_windy.obciazenie - 1)
            self.statystyki["liczba_wyjsc_z_windy"] += 1
            self._zaloguj("wyjscie_z_windy", {
                "tick": tick,
                "agent": agent_id,
                "pietro": pietro,
            })

    def _wpusc_agentow_do_windy(self, pietro: int, tick: int) -> None:
        wolne_miejsca = self.silnik_windy.maks_pojemnosc - self.silnik_windy.obciazenie
        if wolne_miejsca <= 0:
            return

        if pietro == self.ustawienia.pietro_parteru:
            kierunek = "gora"
        else:
            kierunek = "dol"

        kandydaci = self.kolejki.pobierz_pierwszych(pietro, kierunek, wolne_miejsca)

        for agent_id in kandydaci:
            agent = self.agenci[agent_id]

            if agent_id in self.agenci_w_windzie:
                continue

            self.kolejki.usun(agent_id, pietro, kierunek)
            agent.rozpocznij_przejazd_winda(tick)
            self.agenci_w_windzie.append(agent_id)
            self.silnik_windy.obciazenie += 1
            self.statystyki["liczba_wejsc_do_windy"] += 1

            if kierunek == "gora":
                self.silnik_windy.dodaj_wybor_z_kabiny_teraz(agent.pietro_domowe, ZrodloZgloszenia.CZLOWIEK)
                self._zarejestruj_wybor_kabiny_ml(tick=tick, pietro_docelowe=agent.pietro_domowe, kierunek="gora")
            else:
                self.silnik_windy.dodaj_wybor_z_kabiny_teraz(self.ustawienia.pietro_parteru, ZrodloZgloszenia.CZLOWIEK)
                self._zarejestruj_wybor_kabiny_ml(tick=tick, pietro_docelowe=self.ustawienia.pietro_parteru, kierunek="dol")

            self._zaloguj("wejscie_do_windy", {
                "tick": tick,
                "agent": agent_id,
                "pietro": pietro,
                "kierunek": kierunek,
                "cel": agent.cel_pietro if agent.cel_pietro is not None else (
                    agent.pietro_domowe if kierunek == "gora" else self.ustawienia.pietro_parteru
                ),
                "zrodlo_w_systemie_windy": "CZLOWIEK",
            })

        self._przelicz_pozycje_w_kolejce(pietro, kierunek)

    def _przelicz_pozycje_w_kolejce(self, pietro: int, kierunek: str) -> None:
        pozycje = self.kolejki.aktualizuj_pozycje_pozostalych(pietro, kierunek)
        for agent_id, pozycja in pozycje.items():
            self.agenci[agent_id].zaktualizuj_pozycje_w_kolejce(pozycja)

    def _zaloguj(self, typ: str, payload: dict) -> None:
        self.log_zdarzen.append({
            "typ": typ,
            "payload": payload,
        })

    def ostatnie_zdarzenia(self, limit: int = 12) -> list[dict]:
        return list(self.log_zdarzen)[-limit:]

    def snapshot(self) -> dict:
        licznik_stanow = {}
        for agent in self.agenci.values():
            licznik_stanow[agent.stan.name] = licznik_stanow.get(agent.stan.name, 0) + 1

        return {
            "liczba_agentow": len(self.agenci),
            "liczba_agentow_w_windzie": len(self.agenci_w_windzie),
            "liczba_rekordow_ml": self.rejestrator_ml.liczba_rekordow(),
            "kolejki": self.kolejki.snapshot(),
            "stany_agentow": licznik_stanow,
            "statystyki": dict(self.statystyki),
            "metryki_zbiorcze": self._agreguj_metryki(),
            "agenci": {agent_id: agent.snapshot() for agent_id, agent in self.agenci.items()},
        }
