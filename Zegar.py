import tkinter as tk
from Konfiguracja_windy import ParametryWindy
from Silnik_windy import SilnikWindy
from Kierunki_i_typy import Kierunek, ZrodloZgloszenia
from Czas_symulacji import CzasSymulacji, NAZWY_DNI_TYGODNIA

class SymulatorWindyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Symulator Windy - Zegar Systemowy")
        self.root.configure(bg="#f0f2f5")
        
        # --- 1. Inicjalizacja Backendu (Najpierw parametry!) ---
        self.parametry = ParametryWindy(
            liczba_pieter=10,
            pietro_startowe=0,
            ticki_przejazdu_na_pietro=4, 
            ticki_postoju=2,
            maks_pojemnosc=8,
            poczatkowe_obciazenie=0
        )
        self.winda = SilnikWindy(parametry=self.parametry)
        
        # Inicjalizacja czasu symulacji (Poniedziałek, 08:00:00)
        self.czas_sym = CzasSymulacji(dzien_tygodnia_startowy=0, sekunda_dnia_startowa=8 * 3600)
        
        self.symulacja_dziala = False
        self.interwal_ticku_ms = 400
        self.after_id = None 
        
        # --- 2. Budowa Interfejsu ---
        # Panel Zegara
        self.panel_zegara = tk.Frame(root, bg="#202124", pady=15)
        self.panel_zegara.pack(side=tk.TOP, fill=tk.X)
        
        self.lbl_zegar = tk.Label(self.panel_zegara, text="00:00:00", font=("Consolas", 36, "bold"), bg="#202124", fg="#ffffff")
        self.lbl_zegar.pack()
        self.lbl_dzien = tk.Label(self.panel_zegara, text="PONIEDZIAŁEK", font=("Segoe UI", 12, "bold"), bg="#202124", fg="#81c995")
        self.lbl_dzien.pack()

        # Główny kontener
        self.main_container = tk.Frame(root, bg="#f0f2f5")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Przyciski sterowania
        self.panel_ctrl = tk.Frame(self.main_container, bg="#f0f2f5")
        self.panel_ctrl.pack(pady=10)
        
        self.btn_play = tk.Button(self.panel_ctrl, text="Start", command=self.przelacz, width=10, bg="#81c995", fg="white", font=("Segoe UI", 10, "bold"))
        self.btn_play.pack(side=tk.LEFT, padx=5)
        
        tk.Button(self.panel_ctrl, text="Krok +1", command=self.krok, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(self.panel_ctrl, text="Reset", command=self.reset, width=10, bg="#f28b82", fg="white").pack(side=tk.LEFT, padx=5)

        # Wyświetlacz informacji
        self.lbl_info = tk.Label(self.main_container, text="Tick: 0", font=("Segoe UI", 11), bg="#f0f2f5")
        self.lbl_info.pack(pady=10)

        self.odswiez_widok()

    def przelacz(self):
        self.symulacja_dziala = not self.symulacja_dziala
        self.btn_play.config(text="Stop" if self.symulacja_dziala else "Start", bg="#f28b82" if self.symulacja_dziala else "#81c995")
        if self.symulacja_dziala:
            self.petla()

    def petla(self):
        if self.symulacja_dziala:
            self.krok()
            self.after_id = self.root.after(self.interwal_ticku_ms, self.petla)

    def krok(self):
        self.winda.krok()
        self.odswiez_widok()

    def reset(self):
        """Metoda resetująca - teraz bezpieczna dzięki self.parametry"""
        self.symulacja_dziala = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
        
        # Ponowna inicjalizacja windy z zapamiętanymi parametrami
        self.winda = SilnikWindy(self.parametry)
        self.btn_play.config(text="Start", bg="#81c995")
        self.odswiez_widok()

    def odswiez_widok(self):
        stan = self.winda.snapshot()
        # Ważne: SilnikWindy przechowuje aktualny_tick
        tick = self.winda.aktualny_tick
        
        # 1. Przetworzenie ticków na czas przy użyciu CzasSymulacji
        dane_czasu = self.czas_sym.tick_na_czas(tick)
        
        # 2. Aktualizacja zegara
        godz_str = f"{dane_czasu['godzina']:02d}:{dane_czasu['minuta']:02d}:{dane_czasu['sekunda']:02d}"
        self.lbl_zegar.config(text=godz_str)
        
        # 3. Aktualizacja dnia
        nazwa_dnia = NAZWY_DNI_TYGODNIA[dane_czasu['dzien_tygodnia']].upper()
        self.lbl_dzien.config(text=nazwa_dnia)
        
        # 4. Aktualizacja ticku w info
        self.lbl_info.config(text=f"Aktualny Tick: {tick}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SymulatorWindyGUI(root)
    root.mainloop()