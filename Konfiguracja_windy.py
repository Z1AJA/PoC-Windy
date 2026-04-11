from dataclasses import dataclass


@dataclass(slots=True)
class ParametryWindy:
    liczba_pieter: int = 15
    pietro_startowe: int = 0
    ticki_przejazdu_na_pietro: int = 4
    ticki_postoju: int = 4
    maks_pojemnosc: int = 6
    poczatkowe_obciazenie: int = 0

    def __post_init__(self) -> None:
        if self.liczba_pieter < 2:
            raise ValueError("liczba_pieter musi być >= 2")
        if not (0 <= self.pietro_startowe < self.liczba_pieter):
            raise ValueError("pietro_startowe poza zakresem")
        if self.ticki_przejazdu_na_pietro <= 0:
            raise ValueError("ticki_przejazdu_na_pietro musi być > 0")
        if self.ticki_postoju < 0:
            raise ValueError("ticki_postoju nie może być < 0")
        if self.maks_pojemnosc <= 0:
            raise ValueError("maks_pojemnosc musi być > 0")
        if not (0 <= self.poczatkowe_obciazenie <= self.maks_pojemnosc):
            raise ValueError("poczatkowe_obciazenie poza zakresem 0..maks_pojemnosc")
