PoC-Windy — uporządkowany projekt

Uruchamianie:
- GUI: python scripts/Uruchom_GUI.py
- Symulacja konsolowa: python scripts/Uruchom_symulacje_konsolowa.py
- Turbo test: python scripts/Uruchom_turbo_test.py

Struktura:
- src/ kod źródłowy
- scripts/ uruchamianie
- tests/ testy jednostkowe
- data/Plany_zajec/ dane wejściowe
- assets/ obrazy
- reports/ raporty i debug

Uwaga:
- Zgłoszenia generowane przez agentów są oznaczone jako CZLOWIEK, bo symulują realne naciśnięcia przycisków.
- Wewnętrzna „wiedza o agentach” służy wyłącznie do debugowania i testów, nie jako docelowy interfejs uczenia.
