from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from Konfiguracja_windy import ParametryWindy
from Kierunki_i_typy import Kierunek, TypZgloszenia, ZrodloZgloszenia
from Strategia_windy import StrategiaZbiorcza
from Zgloszenia_windy import ZgloszenieWindy


class SilnikWindy:
    def __init__(self, parametry: ParametryWindy, strategia: Optional[StrategiaZbiorcza] = None) -> None:
        self.parametry = parametry
        self.strategia = strategia or StrategiaZbiorcza()

        self.aktualny_tick: int = 0
        self.aktualne_pietro: int = parametry.pietro_startowe
        self.kierunek: Kierunek = Kierunek.BEZRUCH

        self.czy_jedzie: bool = False
        self.czy_stoi_na_przystanku: bool = False

        self.ticki_do_nastepnego_pietra: int = 0
        self.ticki_postoju_pozostale: int = 0

        self.obciazenie: int = parametry.poczatkowe_obciazenie
        self.maks_pojemnosc: int = parametry.maks_pojemnosc

        self.wezwania_gora: Set[int] = set()
        self.wezwania_dol: Set[int] = set()
        self.wybory_z_kabiny: Set[int] = set()

        self.aktywne_klucze_zgloszen: Set[Tuple] = set()
        self.zgloszenia_po_kluczu: Dict[Tuple, List[ZgloszenieWindy]] = {}

    def dodaj_zgloszenie(self, zgloszenie: ZgloszenieWindy) -> bool:
        self._sprawdz_zgloszenie(zgloszenie)

        self.zgloszenia_po_kluczu.setdefault(zgloszenie.klucz_deduplicacji, []).append(zgloszenie)

        if zgloszenie.klucz_deduplicacji in self.aktywne_klucze_zgloszen:
            return False

        self.aktywne_klucze_zgloszen.add(zgloszenie.klucz_deduplicacji)

        if zgloszenie.typ_zgloszenia == TypZgloszenia.WEZWANIE_Z_PIETRA:
            if zgloszenie.kierunek == Kierunek.GORA:
                self.wezwania_gora.add(zgloszenie.pietro)
            else:
                self.wezwania_dol.add(zgloszenie.pietro)
        else:
            self.wybory_z_kabiny.add(zgloszenie.pietro_docelowe)

        if not self.czy_jedzie and not self.czy_stoi_na_przystanku:
            self._rusz_jezeli_mozna()

        return True
    
    def dodaj_wezwanie_z_pietra_teraz(
        self,
        pietro: int,
        kierunek: Kierunek,
        zrodlo: ZrodloZgloszenia,
    ) -> bool:
        zgloszenie = ZgloszenieWindy(
            typ_zgloszenia=TypZgloszenia.WEZWANIE_Z_PIETRA,
            zrodlo=zrodlo,
            tick_utworzenia=self.aktualny_tick,
            pietro=pietro,
            kierunek=kierunek,
        )
        return self.dodaj_zgloszenie(zgloszenie)

    def dodaj_wybor_z_kabiny_teraz(
        self,
        pietro_docelowe: int,
        zrodlo: ZrodloZgloszenia,
    ) -> bool:
        zgloszenie = ZgloszenieWindy(
            typ_zgloszenia=TypZgloszenia.WYBOR_Z_KABINY,
            zrodlo=zrodlo,
            tick_utworzenia=self.aktualny_tick,
            pietro=self.aktualne_pietro,
            pietro_docelowe=pietro_docelowe,
        )
        return self.dodaj_zgloszenie(zgloszenie)

    def krok(self) -> None:
        self.aktualny_tick += 1

        if self.czy_stoi_na_przystanku:
            self.ticki_postoju_pozostale -= 1
            if self.ticki_postoju_pozostale <= 0:
                self.czy_stoi_na_przystanku = False
                self._rusz_jezeli_mozna()
            return

        if self.czy_jedzie:
            self.ticki_do_nastepnego_pietra -= 1

            if self.ticki_do_nastepnego_pietra <= 0:
                self.aktualne_pietro += self.kierunek.value

                if self._czy_powinien_sie_tu_zatrzymac():
                    self._obsluz_biezace_pietro()
                    self.czy_jedzie = False
                    self.czy_stoi_na_przystanku = True
                    self.ticki_postoju_pozostale = self.parametry.ticki_postoju
                else:
                    nowy_kierunek = self.strategia.wybierz_kierunek(self)
                    if nowy_kierunek == Kierunek.BEZRUCH:
                        self.czy_jedzie = False
                        self.kierunek = Kierunek.BEZRUCH
                    else:
                        self.kierunek = nowy_kierunek
                        self.ticki_do_nastepnego_pietra = self.parametry.ticki_przejazdu_na_pietro
            return

        self._rusz_jezeli_mozna()

    def snapshot(self) -> dict:
        return {
            "tick": self.aktualny_tick,
            "aktualne_pietro": self.aktualne_pietro,
            "kierunek": self.kierunek.name,
            "czy_jedzie": self.czy_jedzie,
            "czy_stoi_na_przystanku": self.czy_stoi_na_przystanku,
            "ticki_do_nastepnego_pietra": self.ticki_do_nastepnego_pietra,
            "ticki_postoju_pozostale": self.ticki_postoju_pozostale,
            "obciazenie": self.obciazenie,
            "maks_pojemnosc": self.maks_pojemnosc,
            "oczekujace": {
                "wezwania_gora": sorted(self.wezwania_gora),
                "wezwania_dol": sorted(self.wezwania_dol),
                "wybory_z_kabiny": sorted(self.wybory_z_kabiny),
            },
            "liczba_aktywnych_zgloszen": self.liczba_aktywnych_zgloszen(),
        }

    def liczba_aktywnych_zgloszen(self) -> int:
        return len(self.aktywne_klucze_zgloszen)

    def ma_oczekujace(self) -> bool:
        return bool(self.wezwania_gora or self.wezwania_dol or self.wybory_z_kabiny)

    def ma_oczekujace_wyzej(self, pietro: int) -> bool:
        return any(f > pietro for f in self._wszystkie_oczekujace_pietra())

    def ma_oczekujace_nizej(self, pietro: int) -> bool:
        return any(f < pietro for f in self._wszystkie_oczekujace_pietra())

    def najblizsze_oczekujace_pietro(self) -> Optional[int]:
        oczekujace = self._wszystkie_oczekujace_pietra()
        if not oczekujace:
            return None
        return min(oczekujace, key=lambda f: (abs(f - self.aktualne_pietro), f))

    def _wszystkie_oczekujace_pietra(self) -> Set[int]:
        return set(self.wezwania_gora) | set(self.wezwania_dol) | set(self.wybory_z_kabiny)

    def _sprawdz_zgloszenie(self, zgloszenie: ZgloszenieWindy) -> None:
        pietra_do_sprawdzenia = [zgloszenie.pietro]
        if zgloszenie.pietro_docelowe is not None:
            pietra_do_sprawdzenia.append(zgloszenie.pietro_docelowe)

        for pietro in pietra_do_sprawdzenia:
            if not (0 <= pietro < self.parametry.liczba_pieter):
                raise ValueError(f"Piętro {pietro} poza zakresem 0..{self.parametry.liczba_pieter - 1}")

    def _rusz_jezeli_mozna(self) -> None:
        if self.czy_jedzie or self.czy_stoi_na_przystanku:
            return

        if not self.ma_oczekujace():
            self.kierunek = Kierunek.BEZRUCH
            return

        if self._czy_powinien_sie_tu_zatrzymac():
            self._obsluz_biezace_pietro()
            self.czy_stoi_na_przystanku = True
            self.ticki_postoju_pozostale = self.parametry.ticki_postoju
            return

        kierunek = self.strategia.wybierz_kierunek(self)
        if kierunek == Kierunek.BEZRUCH:
            return

        nastepne_pietro = self.aktualne_pietro + kierunek.value
        if not (0 <= nastepne_pietro < self.parametry.liczba_pieter):
            self.kierunek = Kierunek.BEZRUCH
            return

        self.kierunek = kierunek
        self.czy_jedzie = True
        self.ticki_do_nastepnego_pietra = self.parametry.ticki_przejazdu_na_pietro

    def _czy_powinien_sie_tu_zatrzymac(self) -> bool:
        pietro = self.aktualne_pietro

        if pietro in self.wybory_z_kabiny:
            return True

        if self.kierunek == Kierunek.GORA:
            if pietro in self.wezwania_gora:
                return True
            if pietro in self.wezwania_dol and not self.ma_oczekujace_wyzej(pietro):
                return True
            return False

        if self.kierunek == Kierunek.DOL:
            if pietro in self.wezwania_dol:
                return True
            if pietro in self.wezwania_gora and not self.ma_oczekujace_nizej(pietro):
                return True
            return False

        return pietro in self.wezwania_gora or pietro in self.wezwania_dol

    def _obsluz_biezace_pietro(self) -> None:
        pietro = self.aktualne_pietro
        obsluzone_klucze: List[Tuple] = []

        klucz_kabina = ("KABINA", pietro)
        klucz_wezwanie_gora = ("WEZWANIE", pietro, Kierunek.GORA)
        klucz_wezwanie_dol = ("WEZWANIE", pietro, Kierunek.DOL)

        if pietro in self.wybory_z_kabiny:
            self.wybory_z_kabiny.remove(pietro)
            obsluzone_klucze.append(klucz_kabina)

        if self.kierunek == Kierunek.GORA:
            if pietro in self.wezwania_gora:
                self.wezwania_gora.remove(pietro)
                obsluzone_klucze.append(klucz_wezwanie_gora)
            if pietro in self.wezwania_dol and not self.ma_oczekujace_wyzej(pietro):
                self.wezwania_dol.remove(pietro)
                obsluzone_klucze.append(klucz_wezwanie_dol)

        elif self.kierunek == Kierunek.DOL:
            if pietro in self.wezwania_dol:
                self.wezwania_dol.remove(pietro)
                obsluzone_klucze.append(klucz_wezwanie_dol)
            if pietro in self.wezwania_gora and not self.ma_oczekujace_nizej(pietro):
                self.wezwania_gora.remove(pietro)
                obsluzone_klucze.append(klucz_wezwanie_gora)

        else:
            if pietro in self.wezwania_gora:
                self.wezwania_gora.remove(pietro)
                obsluzone_klucze.append(klucz_wezwanie_gora)
            if pietro in self.wezwania_dol:
                self.wezwania_dol.remove(pietro)
                obsluzone_klucze.append(klucz_wezwanie_dol)

        for klucz in obsluzone_klucze:
            self.aktywne_klucze_zgloszen.discard(klucz)
            self.zgloszenia_po_kluczu.pop(klucz, None)
