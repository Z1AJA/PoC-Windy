# Projekt „winda” — instrukcja techniczna dla warstwy GUI i wizualizacji (PoC)

## 1. Po co jest ten dokument

Ten dokument ma dać Ci wszystko, czego potrzebujesz do wykonania warstwy GUI w naszym PoC projektu inteligentnej windy. Ma nie tylko powiedzieć „co kliknąć”, ale przede wszystkim wyjaśnić, jak myśleć o integracji z silnikiem, jakie dane już mamy, czego nie wolno psuć, gdzie masz swobodę projektową i jak sensownie użyć AI, żeby nie generowała przypadkowego kodu.

Ten dokument jest pisany pod osobę, która będzie robiła:

- przyciski wywołania windy z pięter,
- przyciski wewnątrz kabiny,
- wizualizację ruchu windy,
- prostą kontrolę symulacji,
- integrację z istniejącym backendem.

To nie jest jeszcze docelowy produkt. To jest PoC. Ale PoC ma być zrobiony tak, żeby:

- dało się go pokazać,
- dało się go rozwijać,
- dało się na nim testować kolejne wersje projektu,
- nie trzeba było go potem wyrzucać do kosza.

---

## 2. Krótkie streszczenie całego projektu

Projekt dotyczy inteligentnej windy, która w kolejnych etapach ma skracać czas oczekiwania na podstawie danych o ruchu ludzi w budynku.

W praktyce myślimy o tym tak:

1. Mamy silnik jednej windy.
2. Mamy symulację czasu.
3. Mamy zgłoszenia od ludzi lub systemu.
4. Winda podejmuje decyzje i porusza się po piętrach.
5. GUI ma pokazać, co się dzieje, i umożliwić ręczne testowanie.
6. W kolejnych etapach dojdą dane o harmonogramach, symulacje obciążenia, a potem możliwe sterowanie inteligentne.

Na ten moment backend nie jest „AI”, tylko sensownym rdzeniem symulacyjnym. I to jest dobrze. Najpierw trzeba mieć dobrą mechanikę, potem można dokładać inteligencję.

---

## 3. Co już istnieje po stronie backendu

Masz do dyspozycji gotowe pliki backendowe:

- `Silnik_windy.py`
- `Konfiguracja_windy.py`
- `Kierunki_i_typy.py`
- `Zgloszenia_windy.py`
- `Strategia_windy.py`
- `Czas_symulacji.py` — jeśli został już dodany zgodnie z aktualizacją
- `Przyklad_uzycia.py`
- `Opis_silnika_windy.md`

Najważniejszy dla Ciebie jest `Silnik_windy.py`, bo to jest centralny obiekt, z którym GUI ma rozmawiać.

Backend:

- trzyma stan windy,
- przyjmuje zgłoszenia,
- aktualizuje się tick po ticku,
- zwraca bieżący stan w formie `snapshot()`.

GUI nie ma wymyślać własnej logiki windy. GUI ma być warstwą wejścia i prezentacji.

---

## 4. Jak myśleć o podziale odpowiedzialności

To jest bardzo ważne.

### Backend odpowiada za

- stan windy,
- logikę jazdy,
- kolejność obsługi zgłoszeń,
- upływ ticków,
- wiedzę o tym, na którym piętrze jest winda,
- wiedzę o tym, czy winda jedzie czy stoi,
- deduplikację zgłoszeń,
- strategię sterowania.

### GUI odpowiada za

- wyświetlenie stanu,
- przyjmowanie kliknięć użytkownika,
- przekazywanie komend do backendu,
- odświeżanie obrazu po zmianie stanu,
- opcjonalnie sterowanie szybkością symulacji.

### Czego GUI nie powinno robić

- przechowywać „drugiej wersji prawdy” o stanie windy,
- samodzielnie decydować, gdzie winda pojedzie,
- zmieniać bezpośrednio pól obiektu `SilnikWindy`,
- implementować własnej logiki ruchu,
- ręcznie budować stanu, który powinien pochodzić z `snapshot()`.

Najprościej:

- backend = logika i prawda,
- GUI = widok i wejście.

---

## 5. Główny obiekt, z którym pracujesz

Po stronie GUI pracujesz na obiekcie klasy:

```python
winda = SilnikWindy(parametry)
```

Czyli typowy start będzie wyglądał mniej więcej tak:

```python
from Konfiguracja_windy import ParametryWindy
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
```

Twoje GUI dostaje ten obiekt i pracuje wyłącznie przez jego publiczne metody.

---

## 6. Jakie publiczne metody backendu są istotne dla GUI

To jest najważniejsza sekcja z punktu widzenia integracji.

### 6.1. `krok()`

Ta metoda wykonuje jeden tick symulacji.

```python
winda.krok()
```

Co to oznacza praktycznie:

- aktualny czas symulacji przesuwa się o 1 tick,
- winda może przejechać część drogi lub całe piętro,
- winda może zakończyć postój,
- winda może zacząć ruch,
- stan wewnętrzny się aktualizuje.

GUI powinno wywoływać tę metodę w pętli symulacji.

---

### 6.2. `snapshot()`

Ta metoda zwraca bieżący stan windy jako słownik.

```python
stan = winda.snapshot()
```

To jest podstawowe źródło danych do renderowania.

Przykładowa struktura może wyglądać tak:

```python
{
    "tick": 25,
    "aktualne_pietro": 4,
    "kierunek": "GORA",
    "czy_jedzie": True,
    "czy_stoi_na_przystanku": False,
    "ticki_do_nastepnego_pietra": 2,
    "ticki_postoju_pozostale": 0,
    "obciazenie": 0,
    "maks_pojemnosc": 8,
    "oczekujace": {
        "wezwania_gora": [5, 7],
        "wezwania_dol": [9],
        "wybory_z_kabiny": [8]
    },
    "liczba_aktywnych_zgloszen": 3
}
```

Nie zakładaj nic „na pamięć”. Zawsze renderuj z tego, co da `snapshot()`.

---

### 6.3. `dodaj_wezwanie_z_pietra_teraz(...)`

To metoda do zgłoszenia wezwania windy z piętra.

Zakładany styl użycia:

```python
winda.dodaj_wezwanie_z_pietra_teraz(
    pietro=3,
    kierunek=Kierunek.GORA,
    zrodlo=ZrodloZgloszenia.CZLOWIEK,
)
```

To ma być podstawowa metoda pod przyciski na korytarzach.

Czyli:

- użytkownik klika „góra” na piętrze 3,
- GUI wywołuje tę metodę,
- backend sam nadaje tick utworzenia i zajmuje się resztą.

---

### 6.4. `dodaj_wybor_z_kabiny_teraz(...)`

To metoda do wyboru piętra z wnętrza windy.

Przykład:

```python
winda.dodaj_wybor_z_kabiny_teraz(
    pietro_docelowe=7,
    zrodlo=ZrodloZgloszenia.CZLOWIEK,
)
```

To ma być pod przyciski wewnętrzne kabiny.

---

## 7. Enumy, które GUI musi znać

W pliku `Kierunki_i_typy.py` są enumy. GUI musi znać ich sens.

### `Kierunek`

Wartości:

- `Kierunek.GORA`
- `Kierunek.DOL`
- `Kierunek.BEZRUCH`

GUI używa tego:

- przy wysyłaniu wezwania z piętra,
- przy wyświetlaniu kierunku windy.

### `ZrodloZgloszenia`

Wartości:

- `ZrodloZgloszenia.CZLOWIEK`
- `ZrodloZgloszenia.SYSTEM`

W GUI zazwyczaj używasz:

- `CZLOWIEK`

`SYSTEM` może się przydać np. do automatycznego generowania testowych zgłoszeń.

### `TypZgloszenia`

Tego GUI zwykle nie musi przekazywać ręcznie, jeśli używa wygodnych metod `dodaj_*_teraz`, ale warto rozumieć różnicę:

- `WEZWANIE_Z_PIETRA`
- `WYBOR_Z_KABINY`

---

## 8. Jak ma wyglądać minimalne GUI na PoC

Minimalna wersja, która już ma sens, powinna mieć trzy obszary.

### 8.1. Panel budynku

Powinien pokazywać:

- wszystkie piętra,
- pozycję windy,
- ewentualnie numer aktualnego piętra,
- ewentualnie kierunek.

Najprostsza wersja:

- pionowa lista pięter,
- prostokąt lub kolorowy blok jako kabina,
- podświetlenie piętra, na którym obecnie jest winda.

Lepsza wersja:

- animacja przejazdu między piętrami,
- osobny znacznik kierunku,
- wizualne zaznaczenie oczekujących zgłoszeń na piętrach.

---

### 8.2. Panel przycisków zewnętrznych

Dla każdego piętra:

- przycisk `GÓRA`
- przycisk `DÓŁ`

Ale praktycznie:

- na najwyższym piętrze nie ma sensu pokazywać `GÓRA`,
- na najniższym nie ma sensu pokazywać `DÓŁ`.

Kliknięcie ma wywoływać:

```python
winda.dodaj_wezwanie_z_pietra_teraz(...)
```

---

### 8.3. Panel przycisków kabiny

Lista pięter dostępnych w kabinie.

Kliknięcie ma wywoływać:

```python
winda.dodaj_wybor_z_kabiny_teraz(...)
```

Dobrze, jeśli GUI:

- nie blokuje przycisków już klikniętych na stałe,
- ale może je wizualnie zaznaczać jako oczekujące.

---

## 9. Co jeszcze warto mieć w GUI, choć nie jest konieczne

To są dobre dodatki do PoC:

- przycisk start/pauza,
- przycisk pojedynczego kroku,
- suwak lub wybór szybkości symulacji,
- podgląd aktualnego ticka,
- podgląd czasu przeliczonego przez `CzasSymulacji`,
- lista oczekujących zgłoszeń,
- podgląd parametryzacji windy,
- przycisk resetu symulacji.

Nie musisz robić wszystkiego, ale te elementy są sensowne.

---

## 10. Jak myśleć o animacji ruchu windy

Bardzo ważna rzecz: backend operuje na poziomie pięter i ticków, a nie płynnej fizyki piksel po pikselu.

To oznacza, że GUI ma dwa rozsądne warianty.

### Wariant A — prosty

Pokazujesz windę tylko na aktualnym piętrze.
Jeśli backend mówi `aktualne_pietro = 4`, rysujesz ją na wysokości piętra 4.

To jest najprostsze i wystarczy do bardzo prostego PoC.

### Wariant B — lepszy

Używasz:

- `aktualne_pietro`
- `ticki_do_nastepnego_pietra`
- `ticki_przejazdu_na_pietro`

i na tej podstawie interpolujesz pozycję kabiny między piętrami.

To znaczy:

- jeśli winda jedzie z 3 na 4,
- i zostało 1 z 3 ticków,
- możesz narysować ją już bliżej piętra 4 niż 3.

To będzie wyglądało lepiej, ale nadal nie wymaga zmiany backendu.

Jeśli robisz PoC szybko, zacznij od wariantu A.
Jeśli starczy czasu, dołóż wariant B.

---

## 11. Pętla działania aplikacji GUI

To powinno działać mniej więcej tak:

1. użytkownik klika przycisk,
2. GUI wysyła zgłoszenie do backendu,
3. timer GUI lub pętla wywołuje `winda.krok()`,
4. GUI pobiera `snapshot()`,
5. GUI renderuje nowy stan,
6. powtarzamy.

Schemat logiczny:

```python
def aktualizacja():
    winda.krok()
    stan = winda.snapshot()
    renderuj(stan)
```

To może być odpalane:

- co 100 ms,
- co 200 ms,
- lub innym interwałem, zależnie od narzędzia GUI.

Uwaga: 1 tick symulacji nie musi oznaczać 1 klatki ekranu. Możesz mieć:

- 1 tick = 1 sekunda logiki,
- ale renderowanie częściej lub rzadziej.

Na PoC można przyjąć prosty model:

- co jedno odświeżenie GUI robisz jeden `krok()`.

---

## 12. Jak wykorzystać `Czas_symulacji.py`

Jeśli plik `Czas_symulacji.py` jest już dodany, to jego zadaniem nie jest sterowanie windą, tylko tłumaczenie ticka na sensowny czas.

To znaczy:

- backend zna `aktualny_tick`,
- warstwa czasu tłumaczy to na:
  - dzień tygodnia,
  - godzinę,
  - minutę,
  - sekundę.

Przykład użycia:

```python
czas = CzasSymulacji(
    dzien_tygodnia_startowy=0,
    sekunda_dnia_startowa=7 * 3600 + 30 * 60,
)

opis_czasu = czas.tick_na_czas(winda.aktualny_tick)
```

I wtedy GUI może pokazać np.:

- `poniedziałek`
- `07:30:25`

To jest przydatne później, gdy będziemy wiązać symulację z ruchem studentów zależnym od godzin i dni tygodnia.

Na ten moment to warstwa pomocnicza, ale bardzo dobra do prezentacji.

---

## 13. Czego GUI absolutnie nie powinno zepsuć

To sekcja krytyczna.

### Nie rób tego

- nie zmieniaj bezpośrednio `winda.aktualne_pietro`,
- nie zmieniaj bezpośrednio `winda.kierunek`,
- nie wrzucaj nic ręcznie do `wezwania_gora`, `wezwania_dol`, `wybory_z_kabiny`,
- nie twórz równoległego „lokalnego stanu” windy, który mógłby się rozjechać,
- nie rób własnego planowania trasy po stronie GUI,
- nie zakładaj, że kliknięcie przycisku zawsze od razu ruszy windę.

GUI powinno być cienką warstwą nad backendem.

---

## 14. Co jest już ustalone, a co zostawiamy otwarte

### Ustalone

- jedna winda,
- backend steruje ruchem,
- GUI korzysta z `snapshot()`,
- zgłoszenia dodajemy przez wygodne metody `dodaj_*_teraz`,
- tick jest podstawową jednostką czasu symulacji.

### Otwarte

- jaka technologia GUI zostanie użyta,
- jak dokładnie będzie wyglądać wizualizacja,
- czy ma być interpolacja ruchu,
- czy przyciski mają zmieniać kolor po aktywacji,
- czy dodajemy panel debugowania,
- czy pokazujemy czas symulacyjny stale na ekranie,
- jak wygląda layout.

Czyli: logika jest wspólna, ale forma GUI jest do decyzji.

---

## 15. Najbardziej sensowna ścieżka implementacji GUI

Polecam robić to etapami.

### Etap 1 — integracja podstawowa

Cel:

- uruchomić okno,
- stworzyć obiekt `SilnikWindy`,
- dodać timer,
- po timerze wywoływać `krok()`,
- po każdym kroku pobierać `snapshot()`.

Jeśli to działa, masz już szkielet.

### Etap 2 — wizualizacja budynku

Cel:

- narysować listę pięter,
- narysować kabinę,
- pokazać, na którym piętrze aktualnie jest winda,
- pokazać kierunek.

### Etap 3 — przyciski zewnętrzne

Cel:

- podpiąć przyciski „góra/dół” do metod backendu,
- zobaczyć, że kliknięcie wpływa na trasę windy.

### Etap 4 — przyciski kabiny

Cel:

- dodać wybór pięter z wnętrza windy.

### Etap 5 — informacje dodatkowe

Cel:

- licznik ticków,
- czas symulacji,
- oczekujące zgłoszenia,
- stan jazdy.

### Etap 6 — dopracowanie

Cel:

- estetyka,
- czytelność,
- ewentualna animacja,
- panel debugowania.

To podejście minimalizuje chaos.

---

## 16. Jak wykorzystać wszystkie rzeczy, które już powstały

To jest ważne, bo nie chcemy duplikować roboty.

### `Silnik_windy.py`

To Twój backend. Nie przepisywać. Nie zastępować. Używać.

### `Konfiguracja_windy.py`

To źródło parametrów startowych windy.
Możesz dzięki temu łatwo testować różne ustawienia:

- liczbę pięter,
- prędkość jazdy,
- czas postoju.

### `Kierunki_i_typy.py`

To wspólny język projektu. Używaj enumów stamtąd, nie twórz własnych stringów typu `"UP"` czy `"DOWN"`.

### `Zgloszenia_windy.py`

To model danych zgłoszenia. GUI nie powinno zwykle tworzyć go ręcznie, ale warto rozumieć, co backend przyjmuje.

### `Strategia_windy.py`

To logika jazdy. Nie przenosić jej do GUI. Ale warto wiedzieć, że istnieje, żeby rozumieć zachowanie windy.

### `Czas_symulacji.py`

To warstwa pomocnicza do prezentacji czasu i późniejszej integracji z harmonogramami.

### `Przyklad_uzycia.py`

To dobry punkt odniesienia, jak backend jest używany bez GUI. Można potraktować to jako najprostszy model integracji.

### `Opis_silnika_windy.md`

To dokumentacja rdzenia. Warto mieć go pod ręką przy pracy.

---

## 17. Przykład integracji — bardzo prosty szkic mentalny

To nie jest gotowy kod pod konkretną bibliotekę GUI, tylko wzorzec myślenia.

```python
parametry = ParametryWindy(...)
winda = SilnikWindy(parametry)
czas = CzasSymulacji(...)

def klikniecie_wezwanie_gora(pietro):
    winda.dodaj_wezwanie_z_pietra_teraz(
        pietro=pietro,
        kierunek=Kierunek.GORA,
        zrodlo=ZrodloZgloszenia.CZLOWIEK,
    )

def klikniecie_wezwanie_dol(pietro):
    winda.dodaj_wezwanie_z_pietra_teraz(
        pietro=pietro,
        kierunek=Kierunek.DOL,
        zrodlo=ZrodloZgloszenia.CZLOWIEK,
    )

def klikniecie_kabina(pietro_docelowe):
    winda.dodaj_wybor_z_kabiny_teraz(
        pietro_docelowe=pietro_docelowe,
        zrodlo=ZrodloZgloszenia.CZLOWIEK,
    )

def aktualizacja():
    winda.krok()
    stan = winda.snapshot()
    opis_czasu = czas.tick_na_czas(winda.aktualny_tick)
    renderuj(stan, opis_czasu)
```

To jest sedno całej integracji.

---

## 18. Jak sensownie użyć LLM do pracy nad GUI

AI ma pomóc, a nie zaciemnić obraz. Dlatego prompty muszą być konkretne.

Poniżej są gotowe prompty, ale nie jako „zrób wszystko za mnie”, tylko jako narzędzia do pracy.

---

## 19. Prompt 1 — wybór sensownej architektury GUI

```text
Pracuję nad projektem PoC windy w Pythonie.

Mam gotowy backend:
- obiekt `SilnikWindy`
- metodę `krok()`
- metodę `snapshot()`
- metodę `dodaj_wezwanie_z_pietra_teraz(...)`
- metodę `dodaj_wybor_z_kabiny_teraz(...)`

Backend odpowiada za logikę, a GUI ma odpowiadać tylko za:
- input użytkownika,
- wizualizację,
- pętlę aktualizacji.

Zaproponuj architekturę GUI dla tego projektu.
Uwzględnij:
- podział na moduły / klasy,
- pętlę odświeżania,
- podpięcie przycisków,
- renderowanie stanu na podstawie `snapshot()`.

Nie zmieniaj backendu.
Nie przenoś logiki windy do GUI.
Pokaż sensowną strukturę projektu i uzasadnij wybór.
```

Do czego służy ten prompt:

- żeby LLM nie próbował wymyślać nowego backendu,
- żeby pomógł rozplanować kod GUI.

---

## 20. Prompt 2 — GUI w konkretnej technologii

```text
Mam projekt PoC windy.

Backend jest gotowy w Pythonie i ma:
- `winda.krok()`
- `winda.snapshot()`
- `winda.dodaj_wezwanie_z_pietra_teraz(...)`
- `winda.dodaj_wybor_z_kabiny_teraz(...)`

Chcę zrobić GUI w [wstaw: Tkinter / PyQt / Pygame].

Wymagania:
- wizualizacja budynku i pozycji windy,
- przyciski wywołania z pięter,
- przyciski wyboru pięter z kabiny,
- aktualizacja stanu co tick,
- brak zmian w backendzie.

Napisz pierwszy działający szkielet aplikacji GUI.
Kod ma być czytelny i podzielony na logiczne sekcje.
```

To jest prompt do wygenerowania pierwszej wersji działającego interfejsu.

---

## 21. Prompt 3 — tylko warstwa wizualizacji

```text
Mam backend windy, który podaje stan przez `snapshot()`.

Przykładowy stan:
- aktualne piętro,
- kierunek,
- informacja czy winda jedzie,
- oczekujące zgłoszenia.

Chcę stworzyć komponent wizualizacji, który:
- rysuje budynek z N piętrami,
- rysuje kabinę windy,
- pokazuje aktualne piętro,
- opcjonalnie pokazuje kierunek i oczekujące wezwania.

Nie twórz logiki windy.
Skup się wyłącznie na komponencie renderującym stan przekazany z backendu.
```

To jest dobry prompt, gdy chcesz odseparować samą wizualizację od całości.

---

## 22. Prompt 4 — podpięcie przycisków do backendu

```text
Mam obiekt `winda` klasy `SilnikWindy`.

Dostępne metody:
- `winda.dodaj_wezwanie_z_pietra_teraz(pietro, kierunek, zrodlo)`
- `winda.dodaj_wybor_z_kabiny_teraz(pietro_docelowe, zrodlo)`

Chcę podłączyć przyciski GUI do tych metod.

Pokaż, jak:
- wygenerować przyciski dla pięter,
- obsłużyć kliknięcie wezwania w górę lub w dół,
- obsłużyć kliknięcie przycisku kabinowego,
- nie dublować logiki backendu.

Kod ma być prosty i czytelny.
```

---

## 23. Prompt 5 — debugowanie GUI

```text
Mam projekt GUI dla symulacji windy.

Backend działa poprawnie.
GUI ma problem:
[tu wklej konkretny problem]

Nie zmieniaj backendu.
Przeanalizuj tylko warstwę GUI, synchronizację odświeżania i podpięcie przycisków.
Pokaż możliwe przyczyny problemu i poprawioną wersję kodu.
```

To jest bardzo ważne, bo inaczej LLM często próbuje „naprawiać wszystko naraz”.

---

## 24. Prompt 6 — poprawa estetyki bez rozwalania architektury

```text
Mam działające GUI dla PoC windy w [Tkinter / PyQt / Pygame].

Nie chcę zmieniać backendu ani architektury aplikacji.
Chcę tylko poprawić:
- czytelność layoutu,
- wygląd przycisków,
- wygląd panelu budynku,
- widoczność aktualnego stanu windy.

Zaproponuj ulepszenia interfejsu, które nie wymagają przebudowy logiki.
Pokaż konkretne zmiany.
```

---

## 25. Prompt 7 — jeśli LLM zacznie odpływać

To jest prompt korygujący, bardzo przydatny.

```text
Nie zmieniaj backendu.
Nie wymyślaj nowego modelu windy.
Nie przenoś logiki ruchu do GUI.
Nie przebudowuj struktury projektu bez potrzeby.

Masz pracować wyłącznie na istniejącym obiekcie `SilnikWindy` i jego publicznych metodach.
GUI ma być cienką warstwą nad backendem.
```

To warto dopisać, gdy model zaczyna „kombinować”.

---

## 26. Jakich błędów AI najczęściej narobi przy takim projekcie

To też warto wiedzieć.

### Typowy błąd 1

LLM zaczyna tworzyć własną klasę windy w GUI.

To jest zły kierunek.

### Typowy błąd 2

LLM próbuje zastąpić enumy stringami typu `"UP"` i `"DOWN"`.

To jest zły kierunek. Mamy już enumy.

### Typowy błąd 3

LLM robi własną logikę trasowania po stronie GUI.

To jest zły kierunek.

### Typowy błąd 4

LLM tworzy ciężką, przekombinowaną architekturę frontendową, która nie daje żadnej wartości przy PoC.

To zwykle zły kierunek.

### Typowy błąd 5

LLM ignoruje `snapshot()` i próbuje czytać pojedyncze pola lub je nadpisywać.

To też zły kierunek.

Jeśli widzisz takie rzeczy, trzeba korygować prompt.

---

## 27. Ile swobody masz po swojej stronie

Nie chcemy narzucać Ci na siłę jednego wyglądu czy jednej technologii.

Masz swobodę w takich rzeczach:

- wybór biblioteki GUI,
- układ okna,
- sposób rysowania windy,
- kolorystyka,
- sposób sygnalizacji aktywnych przycisków,
- sposób uruchamiania i zatrzymywania symulacji,
- panel czasu / panel debug.

Natomiast nie warto rozluźniać tych rzeczy:

- backend pozostaje źródłem prawdy,
- integracja ma opierać się o istniejące publiczne metody,
- stan ma pochodzić ze `snapshot()`.

---

## 28. Co będzie uznane za sukces w PoC

PoC GUI będzie uznane za udane, jeśli:

1. uruchamia się bez kombinacji,
2. da się kliknąć wezwanie z piętra,
3. da się kliknąć wybór piętra w kabinie,
4. winda rzeczywiście reaguje i jedzie,
5. stan na ekranie zgadza się z backendem,
6. da się pokazać ruch i aktualne piętro,
7. całość nie wymaga ręcznych hacków w logice.

To już jest wystarczająco dużo na sensowny pokaz.

---

## 29. Proponowany minimalny zakres pierwszej działającej wersji

Jeśli chcesz działać rozsądnie, zrób najpierw tylko to:

- jedno okno,
- pionowa lista pięter,
- prostokąt reprezentujący windę,
- przyciski zewnętrzne góra/dół,
- przyciski kabinowe,
- timer wywołujący `krok()`,
- odczyt `snapshot()`,
- tekst z numerem piętra i kierunkiem.

Bez:

- ładnych animacji,
- rozbudowanych paneli,
- historii zdarzeń,
- efektów specjalnych.

Najpierw działanie. Potem wygląd.

---

## 30. Podsumowanie najkrótsze z możliwych

Masz zrobić GUI, które:

- wysyła kliknięcia do `SilnikWindy`,
- co jakiś czas wywołuje `krok()`,
- pobiera `snapshot()`,
- rysuje stan windy.

Nie piszesz logiki windy od nowa.
Nie poprawiasz backendu bez potrzeby.
Masz swobodę w formie, ale nie w źródle prawdy.

To ma być warstwa obsługowa i wizualna dla istniejącego silnika.

---

## 31. Kontakt między warstwami — praktyczny kontrakt

Jeśli chcesz myśleć o tym jak o kontrakcie integracyjnym, to jest on bardzo prosty.

### GUI wysyła do backendu

- `dodaj_wezwanie_z_pietra_teraz(...)`
- `dodaj_wybor_z_kabiny_teraz(...)`
- `krok()`

### Backend oddaje do GUI

- `snapshot()`

To już wystarczy do działania PoC.

---

## 32. Ostatnia praktyczna rada

Rób to tak, żeby można było łatwo wymienić samo GUI bez ruszania backendu.

Jeżeli za jakiś czas:

- zmienimy bibliotekę,
- dołożymy ML,
- dołożymy generator ruchu,
- dołożymy więcej paneli diagnostycznych,

to dobrze zrobione GUI nadal będzie używać tego samego backendowego kontraktu.

To jest główny powód, dla którego warto trzymać dyscyplinę już teraz.
