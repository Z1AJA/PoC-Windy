from dataclasses import dataclass


NAZWY_DNI_TYGODNIA = [
    "poniedzialek",
    "wtorek",
    "sroda",
    "czwartek",
    "piatek",
    "sobota",
    "niedziela",
]


@dataclass(slots=True)
class CzasSymulacji:
    dzien_tygodnia_startowy: int = 0
    sekunda_dnia_startowa: int = 0

    def __post_init__(self) -> None:
        if not (0 <= self.dzien_tygodnia_startowy <= 6):
            raise ValueError("dzien_tygodnia_startowy musi być w zakresie 0..6")
        if not (0 <= self.sekunda_dnia_startowa < 86400):
            raise ValueError("sekunda_dnia_startowa musi być w zakresie 0..86399")

    def tick_na_czas(self, tick: int) -> dict:
        if tick < 0:
            raise ValueError("tick nie może być ujemny")

        laczna_liczba_sekund = self.sekunda_dnia_startowa + tick
        przesuniecie_dni = laczna_liczba_sekund // 86400
        sekunda_w_dniu = laczna_liczba_sekund % 86400

        dzien_tygodnia = (self.dzien_tygodnia_startowy + przesuniecie_dni) % 7
        godzina = sekunda_w_dniu // 3600
        minuta = (sekunda_w_dniu % 3600) // 60
        sekunda = sekunda_w_dniu % 60

        return {
            "tick": tick,
            "numer_dnia_symulacji": przesuniecie_dni,
            "dzien_tygodnia": dzien_tygodnia,
            "nazwa_dnia": NAZWY_DNI_TYGODNIA[dzien_tygodnia],
            "godzina": godzina,
            "minuta": minuta,
            "sekunda": sekunda,
            "sekunda_w_dniu": sekunda_w_dniu,
            "czas_tekst": f"{godzina:02d}:{minuta:02d}:{sekunda:02d}",
        }