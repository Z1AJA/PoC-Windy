from Konfiguracja_windy import ParametryWindy
from Kierunki_i_typy import Kierunek, ZrodloZgloszenia, TypZgloszenia
from Silnik_windy import SilnikWindy
from Zgloszenia_windy import ZgloszenieWindy


parametry = ParametryWindy(
    liczba_pieter=10,
    pietro_startowe=0,
    ticki_przejazdu_na_pietro=3,
    ticki_postoju=2,
    maks_pojemnosc=8,
    poczatkowe_obciazenie=0,
)

winda = SilnikWindy(parametry=parametry)

winda.dodaj_zgloszenie(ZgloszenieWindy(
    typ_zgloszenia=TypZgloszenia.WEZWANIE_Z_PIETRA,
    zrodlo=ZrodloZgloszenia.CZLOWIEK,
    tick_utworzenia=0,
    pietro=3,
    kierunek=Kierunek.GORA,
))

winda.dodaj_zgloszenie(ZgloszenieWindy(
    typ_zgloszenia=TypZgloszenia.WYBOR_Z_KABINY,
    zrodlo=ZrodloZgloszenia.CZLOWIEK,
    tick_utworzenia=0,
    pietro=3,
    pietro_docelowe=7,
))

winda.dodaj_zgloszenie(ZgloszenieWindy(
    typ_zgloszenia=TypZgloszenia.WEZWANIE_Z_PIETRA,
    zrodlo=ZrodloZgloszenia.SYSTEM,
    tick_utworzenia=0,
    pietro=5,
    kierunek=Kierunek.DOL,
))

from Czas_symulacji import CzasSymulacji
from Konfiguracja_windy import ParametryWindy
from Kierunki_i_typy import Kierunek, ZrodloZgloszenia
from Silnik_windy import SilnikWindy


parametry = ParametryWindy(
    liczba_pieter=10,
    pietro_startowe=0,
    ticki_przejazdu_na_pietro=3,
    ticki_postoju=2,
    maks_pojemnosc=8,
    poczatkowe_obciazenie=0,
)

winda = SilnikWindy(parametry=parametry)
czas_symulacji = CzasSymulacji(
    dzien_tygodnia_startowy=0,
    sekunda_dnia_startowa=7 * 3600 + 30 * 60,
)

winda.dodaj_wezwanie_z_pietra_teraz(
    pietro=3,
    kierunek=Kierunek.GORA,
    zrodlo=ZrodloZgloszenia.CZLOWIEK,
)


for _ in range(30):
    winda.krok()

    if(winda.aktualny_tick % 7 == 0):
        winda.dodaj_wezwanie_z_pietra_teraz(
        pietro=5,
        kierunek=Kierunek.DOL,
        zrodlo=ZrodloZgloszenia.SYSTEM,
        )

    if(winda.aktualny_tick == 11):
        winda.dodaj_wybor_z_kabiny_teraz(
        pietro_docelowe=7,
        zrodlo=ZrodloZgloszenia.CZLOWIEK,
        )


        
    print(winda.snapshot())
    print(czas_symulacji.tick_na_czas(winda.aktualny_tick))
