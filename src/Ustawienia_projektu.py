from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UstawieniaProjektu:
    seed_glowny: int = 12345
    pietro_parteru: int = 0

    bufor_wyjscia_przed_zajeciami_minuty: int = 15
    prog_powrotu_do_akademika_minuty: int = 120

    bazowe_a_schody_w_dol: float = 0.020
    bazowe_a_schody_w_gore: float = 0.002

    wzrost_rezygnacji_na_tick_w_dol: float = 0.015
    wzrost_rezygnacji_na_tick_w_gore: float = 0.008

    limit_prawdopodobienstwa_schody_w_dol: float = 0.35
    limit_prawdopodobienstwa_schody_w_gore: float = 0.05

    prawdopodobienstwo_losowego_cyklu_dnia: float = 0.25
    minimalna_liczba_losowych_cykli: int = 1
    maksymalna_liczba_losowych_cykli: int = 2
    min_czas_poza_akademikiem_minuty: int = 30
    max_czas_poza_akademikiem_minuty: int = 120
    najwczesniejsza_minuta_losowych_akcji: int = 8 * 60
    najpozniejsza_minuta_losowych_akcji: int = 22 * 60
    minimalny_odstep_od_innych_akcji_minuty: int = 20

    def __post_init__(self) -> None:
        if self.bufor_wyjscia_przed_zajeciami_minuty < 0:
            raise ValueError("bufor_wyjscia_przed_zajeciami_minuty nie może być ujemny")
        if self.prog_powrotu_do_akademika_minuty < 0:
            raise ValueError("prog_powrotu_do_akademika_minuty nie może być ujemny")
        if not (0.0 <= self.prawdopodobienstwo_losowego_cyklu_dnia <= 1.0):
            raise ValueError("prawdopodobienstwo_losowego_cyklu_dnia musi być w zakresie 0..1")
        if self.minimalna_liczba_losowych_cykli < 0:
            raise ValueError("minimalna_liczba_losowych_cykli nie może być ujemna")
        if self.maksymalna_liczba_losowych_cykli < self.minimalna_liczba_losowych_cykli:
            raise ValueError("maksymalna_liczba_losowych_cykli nie może być mniejsza od minimalnej")
        if self.min_czas_poza_akademikiem_minuty <= 0:
            raise ValueError("min_czas_poza_akademikiem_minuty musi być > 0")
        if self.max_czas_poza_akademikiem_minuty < self.min_czas_poza_akademikiem_minuty:
            raise ValueError("max_czas_poza_akademikiem_minuty nie może być mniejszy od minimalnego")
        if self.najpozniejsza_minuta_losowych_akcji <= self.najwczesniejsza_minuta_losowych_akcji:
            raise ValueError("okno losowych akcji jest niepoprawne")
        if self.minimalny_odstep_od_innych_akcji_minuty < 0:
            raise ValueError("minimalny_odstep_od_innych_akcji_minuty nie może być ujemny")

        for nazwa in [
            "bazowe_a_schody_w_dol",
            "bazowe_a_schody_w_gore",
            "wzrost_rezygnacji_na_tick_w_dol",
            "wzrost_rezygnacji_na_tick_w_gore",
            "limit_prawdopodobienstwa_schody_w_dol",
            "limit_prawdopodobienstwa_schody_w_gore",
        ]:
            wartosc = getattr(self, nazwa)
            if wartosc < 0:
                raise ValueError(f"{nazwa} nie może być ujemne")

        for nazwa in [
            "limit_prawdopodobienstwa_schody_w_dol",
            "limit_prawdopodobienstwa_schody_w_gore",
        ]:
            wartosc = getattr(self, nazwa)
            if wartosc > 1:
                raise ValueError(f"{nazwa} nie może być > 1")

    def prawdopodobienstwo_rezygnacji_schodami(
        self,
        pietro: int,
        kierunek: str,
        ticki_czekania: int,
    ) -> float:
        bezpieczne_pietro = max(1, pietro)
        bezpieczne_ticki = max(0, ticki_czekania)

        if kierunek == "dol":
            bazowe = self.bazowe_a_schody_w_dol / bezpieczne_pietro
            mnoznik = 1.0 + self.wzrost_rezygnacji_na_tick_w_dol * bezpieczne_ticki
            return min(self.limit_prawdopodobienstwa_schody_w_dol, bazowe * mnoznik)

        if kierunek == "gora":
            bazowe = self.bazowe_a_schody_w_gore / bezpieczne_pietro
            mnoznik = 1.0 + self.wzrost_rezygnacji_na_tick_w_gore * bezpieczne_ticki
            return min(self.limit_prawdopodobienstwa_schody_w_gore, bazowe * mnoznik)

        raise ValueError("kierunek musi być równy 'dol' albo 'gora'")
