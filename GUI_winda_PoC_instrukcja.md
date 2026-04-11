# 🛗 Projekt „winda” — instrukcja dla GUI (PoC)

## 🎯 Cel Twojej części

Twoim zadaniem jest stworzenie:

1. interfejsu z przyciskami (piętra + kierunki),
2. wizualizacji ruchu windy,
3. integracji z gotowym silnikiem (`SilnikWindy`).

To jest PoC — ma działać, być czytelne i rozszerzalne.

---

## 🧠 Backend — jak działa

Masz gotowy silnik:
- działa w tickach (`krok()` = 1 sekunda)
- przyjmuje zgłoszenia
- trzyma stan
- daje `snapshot()`

---

## 🔌 API, którego używasz

### Tworzenie:
```python
winda = SilnikWindy(parametry)
```

### Dodawanie zgłoszeń:
```python
winda.dodaj_wezwanie_z_pietra_teraz(pietro, kierunek, zrodlo)
winda.dodaj_wybor_z_kabiny_teraz(pietro_docelowe, zrodlo)
```

### Tick:
```python
winda.krok()
```

### Stan:
```python
state = winda.snapshot()
```

---

## 📊 Co masz w snapshot()

- aktualne_pietro
- kierunek
- czy_jedzie
- czy_stoi_na_przystanku
- oczekujące zgłoszenia

To jest jedyne źródło prawdy dla GUI.

---

## 🎮 GUI — minimalne wymagania

- przyciski pięter (góra/dół)
- przyciski w kabinie
- wizualizacja windy (prostokąt)
- animacja między piętrami
- odświeżanie co tick

---

## 🔄 Pętla

```python
while True:
    winda.krok()
    state = winda.snapshot()
    render(state)
```

---

## 🕒 Czas symulacji

Użyj:
```python
czas.tick_na_czas(winda.aktualny_tick)
```

---

## 🚫 Zasady

- nie ruszasz backendu
- nie tworzysz requestów ręcznie
- GUI = tylko input + render

---

## 🤖 Prompty dla AI

### GUI start:
"""
Mam backend windy w Pythonie (krok + snapshot).
Zrób GUI z przyciskami i wizualizacją.
"""

### Integracja:
"""
Podłącz GUI do metod:
- dodaj_wezwanie
- dodaj_wybor
- snapshot
"""

### Wizualizacja:
"""
Narysuj windę w budynku N pięter.
"""

---

## 🧠 Model myślenia

Backend = logika  
GUI = wizualizacja + input

---

## 🚀 Cel

Klik → winda jedzie → widzę ruch.
