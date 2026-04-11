from enum import Enum, auto


class Kierunek(Enum):
    DOL = -1
    BEZRUCH = 0
    GORA = 1


class ZrodloZgloszenia(Enum):
    CZLOWIEK = auto()
    SYSTEM = auto()


class TypZgloszenia(Enum):
    WEZWANIE_Z_PIETRA = auto()
    WYBOR_Z_KABINY = auto()
