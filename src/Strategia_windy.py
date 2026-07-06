from __future__ import annotations
from typing import TYPE_CHECKING
from Kierunki_i_typy import Kierunek

if TYPE_CHECKING:
    from Silnik_windy import SilnikWindy

class StrategiaZbiorcza:
    """
    Prosta strategia dla jednej windy.

    Zasada:
    - jeśli winda jedzie w górę, to po drodze obsługuje:
      * wybory z kabiny na mijanych piętrach,
      * wezwania w górę na mijanych piętrach,
      * wezwania w dół dopiero wtedy, gdy nad windą nie ma już nic do obsługi.
    - analogicznie w dół,
    - jeśli stoi bez kierunku, wybiera najbliższe oczekujące piętro.
    """

    def wybierz_kierunek(self, winda: "SilnikWindy") -> Kierunek:
        biezace_pietro = winda.aktualne_pietro

        cos_wyzej = winda.ma_oczekujace_wyzej(biezace_pietro)
        cos_nizej = winda.ma_oczekujace_nizej(biezace_pietro)

        if winda.kierunek == Kierunek.GORA:
            if cos_wyzej:
                return Kierunek.GORA
            if cos_nizej:
                return Kierunek.DOL
            return Kierunek.BEZRUCH
        

        if winda.kierunek == Kierunek.DOL:
            if cos_nizej:
                return Kierunek.DOL
            if cos_wyzej:
                return Kierunek.GORA
            return Kierunek.BEZRUCH

        najblizsze = winda.najblizsze_oczekujace_pietro()
        if najblizsze is None:
            return Kierunek.BEZRUCH
        if najblizsze > biezace_pietro:
            return Kierunek.GORA
        if najblizsze < biezace_pietro:
            return Kierunek.DOL
        return Kierunek.BEZRUCH
