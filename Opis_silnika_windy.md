# Projekt „winda” — opis rdzenia

## Zawartość projektu

- `Silnik_windy.py` — główna klasa silnika windy.
- `testy_Silnik_windy.py` — testy jednostkowe.
- `Kierunki_i_typy.py` — enumy używane w projekcie.
- `Konfiguracja_windy.py` — parametry fizyczne i techniczne windy.
- `Zgloszenia_windy.py` — klasa pojedynczego zgłoszenia.
- `Strategia_windy.py` — strategia sterowania jedną windą.
- `Przyklad_uzycia.py` — prosty przykład działania.

## Założenia projektu

To jest rdzeń jednej windy działającej na `N` piętrach.

Silnik:

- przyjmuje zgłoszenia od człowieka i systemu,
- rozróżnia wezwania z piętra i wybory piętra z kabiny,
- działa w tickach,
- przechowuje aktualny stan windy,
- daje prosty `snapshot()` pod GUI,
- ma uproszczoną, czytelną strategię jazdy.

Nie ma tu jeszcze:

- wielu wind,
- ML,
- pełnej logiki drzwi,
- logiki przepełnienia,
- centralnego dispatchera.

## Enumy

### `Kierunek`

Opisuje kierunek ruchu windy.

- `DOL` — ruch w dół
- `BEZRUCH` — brak aktywnego ruchu
- `GORA` — ruch w górę

### `ZrodloZgloszenia`

Opisuje źródło zgłoszenia.

- `CZLOWIEK` — zgłoszenie od użytkownika
- `SYSTEM` — zgłoszenie od systemu

### `TypZgloszenia`

Opisuje typ zgłoszenia.

- `WEZWANIE_Z_PIETRA` — ktoś woła windę z piętra i wskazuje kierunek
- `WYBOR_Z_KABINY` — ktoś będąc w windzie wybiera piętro docelowe

To rozróżnienie jest ważne i powinno zostać.

## `ParametryWindy`

Klasa przechowująca parametry fizyczne.

### Pola

- `liczba_pieter` — ile pięter ma budynek
- `pietro_startowe` — od którego piętra startuje winda
- `ticki_przejazdu_na_pietro` — ile ticków trwa przejazd o jedno piętro
- `ticki_postoju` — ile ticków trwa zatrzymanie na piętrze
- `maks_pojemnosc` — maksymalna pojemność
- `poczatkowe_obciazenie` — startowa liczba osób

## `ZgloszenieWindy`

Opisuje pojedyncze zgłoszenie.

### Pola zgloszen

- `typ_zgloszenia` — `WEZWANIE_Z_PIETRA` albo `WYBOR_Z_KABINY`
- `zrodlo` — `CZLOWIEK` albo `SYSTEM`
- `tick_utworzenia` — kiedy powstało zgłoszenie
- `pietro` — piętro źródłowe
- `kierunek` — tylko dla wezwania z piętra
- `pietro_docelowe` — tylko dla wyboru z kabiny
- `id_zgloszenia` — unikalny numer zgłoszenia

### `klucz_deduplicacji`s

Służy do tego, żeby identyczne aktywne zgłoszenia nie tworzyły wielu osobnych przystanków.

- dla wezwania z piętra: `("WEZWANIE", pietro, kierunek)`
- dla wyboru z kabiny: `("KABINA", pietro_docelowe)`

## `StrategiaZbiorcza`

To podstawowa strategia jazdy.

### Jak działa

- jeśli winda jedzie w górę, dalej jedzie w górę tak długo, jak wyżej są oczekujące zgłoszenia,
- jeśli winda jedzie w dół, dalej jedzie w dół tak długo, jak niżej są oczekujące zgłoszenia,
- jeśli stoi, wybiera kierunek do najbliższego oczekującego piętra,
- przy jeździe w górę bierze po drodze wezwania w górę i wybory z kabiny,
- wezwania w dół na tym samym piętrze bierze dopiero wtedy, gdy nad windą nie ma już nic do zrobienia,
- analogicznie przy jeździe w dół.

To jest prosta baza na PoC.

## `SilnikWindy`

To główna klasa projektu.

### Najważniejsze pola

- `aktualny_tick` — aktualny czas symulacji
- `aktualne_pietro` — bieżące piętro
- `kierunek` — aktualny kierunek
- `czy_jedzie` — czy winda jest w ruchu
- `czy_stoi_na_przystanku` — czy trwa postój
- `ticki_do_nastepnego_pietra` — ile zostało do dojechania na kolejne piętro
- `ticki_postoju_pozostale` — ile zostało postoju
- `obciazenie` — bieżąca liczba osób
- `maks_pojemnosc` — maksymalna pojemność
- `wezwania_gora` — zbiór pięter z wezwaniem w górę
- `wezwania_dol` — zbiór pięter z wezwaniem w dół
- `wybory_z_kabiny` — zbiór pięter wybranych z kabiny

### Najważniejsze metody

#### `dodaj_zgloszenie(zgloszenie)`

Dodaje zgłoszenie do systemu.
Zwraca:

- `True` — jeśli doszło nowe aktywne zgłoszenie,
- `False` — jeśli zgłoszenie było duplikatem aktywnego przystanku.

#### `krok()`

Wykonuje jeden tick symulacji.
To główna metoda silnika.

#### `snapshot()`

Zwraca stan windy jako słownik.
To najprostsze API do komunikacji z GUI.

#### `liczba_aktywnych_zgloszen()`

Zwraca liczbę aktywnych, nieobsłużonych zgłoszeń.

#### `ma_oczekujace_wyzej(pietro)`

Sprawdza, czy wyżej są oczekujące zgłoszenia.

#### `ma_oczekujace_nizej(pietro)`

Sprawdza, czy niżej są oczekujące zgłoszenia.

#### `najblizsze_oczekujace_pietro()`

Zwraca najbliższe piętro z oczekującym zgłoszeniem.

## Uproszczona logika jazdy

1. Jeśli winda stoi i nie ma zleceń, nic nie robi.
2. Jeśli stoi i ma zlecenia, wybiera kierunek.
3. Jeśli jedzie, przemieszcza się piętro po piętrze.
4. Po osiągnięciu piętra sprawdza, czy powinna się zatrzymać.
5. Po zatrzymaniu stoi przez `ticki_postoju`.
6. Potem ponownie wybiera ruch.

## Dlaczego ten model ma sens

Bo jest:

- prosty,
- czytelny,
- łatwy do testowania,
- gotowy do podpięcia pod GUI,
- wystarczający na PoC,
- dobry jako baza pod kolejne wersje.
