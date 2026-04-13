import tkinter as tk
from tkinter import ttk
from Konfiguracja_windy import ParametryWindy
from Silnik_windy import SilnikWindy
from Kierunki_i_typy import Kierunek, ZrodloZgloszenia
from Czas_symulacji import CzasSymulacji, NAZWY_DNI_TYGODNIA

class OkraglyPrzycisk(tk.Canvas):
    """Własny komponent okrągłego przycisku oparty na Canvas."""
    def __init__(self, parent, tekst, komenda, promien=22, kolor="#ffffff", kolor_aktywny="#4285f4"):
        super().__init__(parent, width=promien*2, height=promien*2, bg=parent["bg"], 
                         highlightthickness=0, cursor="hand2")
        self.komenda = komenda
        self.kolor = kolor
        self.kolor_aktywny = kolor_aktywny
        
        # Rysowanie koła
        self.owale = self.create_oval(2, 2, promien*2-2, promien*2-2, fill=kolor, outline="#dcdfe6", width=2)
        self.tekst = self.create_text(promien, promien, text=tekst, font=("Segoe UI", 12, "bold"), fill="#333333")
        
        # Zdarzenia
        self.bind("<Button-1>", lambda e: self._klik())
        self.bind("<Enter>", lambda e: self.itemconfig(self.owale, fill="#f8f9fa"))
        self.bind("<Leave>", lambda e: self.itemconfig(self.owale, fill=self.kolor))

    def _klik(self):
        self.itemconfig(self.owale, fill=self.kolor_aktywny)
        self.itemconfig(self.tekst, fill="white")
        self.after(100, lambda: [self.itemconfig(self.owale, fill=self.kolor), 
                                 self.itemconfig(self.tekst, fill="#333333")])
        self.komenda()

class SymulatorWindyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Symulator Inteligentnej Windy (Modern UI)")
        self.kolor_tla = "#f0f2f5" 
        self.root.configure(bg=self.kolor_tla)
        
        # Zmienne dla ustawień
        self.interwal_var = tk.IntVar(value=400)        # ms
        self.pietra_var = tk.IntVar(value=10)           # liczba pięter
        
        # --- 1. Inicjalizacja Backendu ---
        self.parametry = ParametryWindy(liczba_pieter=self.pietra_var.get())
        self.winda = SilnikWindy(parametry=self.parametry)
        self.czas_sym = CzasSymulacji(dzien_tygodnia_startowy=0, sekunda_dnia_startowa=8 * 3600)
        
        self.symulacja_dziala = False
        self.interwal_ticku_ms = self.interwal_var.get()
        self.after_id = None 
        
        # --- Górny pasek: zegar + ustawienia ---
        top_frame = tk.Frame(root, bg="#202124")
        top_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Zegar (lewa strona)
        self.panel_zegara = tk.Frame(top_frame, bg="#202124", pady=5)
        self.panel_zegara.pack(side=tk.LEFT, padx=20)
        self.lbl_zegar = tk.Label(self.panel_zegara, text="08:00:00", font=("Consolas", 28, "bold"), 
                                  bg="#202124", fg="#ffffff")
        self.lbl_zegar.pack()
        self.lbl_dzien = tk.Label(self.panel_zegara, text="PONIEDZIAŁEK", font=("Segoe UI", 11, "bold"), 
                                  bg="#202124", fg="#81c995")
        self.lbl_dzien.pack()
        
        # Panel ustawień (prawa strona)
        ustawienia_frame = tk.Frame(top_frame, bg="#202124", padx=10, pady=5)
        ustawienia_frame.pack(side=tk.RIGHT, padx=20)
        
        # Suwak interwału
        tk.Label(ustawienia_frame, text="Interwał ticku (ms)", bg="#202124", fg="#cccccc", 
                font=("Segoe UI", 9)).grid(row=0, column=0, columnspan=2, pady=(0,2))
        self.scale_interwal = ttk.Scale(ustawienia_frame, from_=1, to=2000, orient=tk.HORIZONTAL,
                                       variable=self.interwal_var, command=self._zmiana_interwalu)
        self.scale_interwal.grid(row=1, column=0, sticky="ew", padx=(0,10))
        self.lbl_interwal = tk.Label(ustawienia_frame, text="400 ms", bg="#202124", fg="white", 
                                     font=("Segoe UI", 9, "bold"), width=7)
        self.lbl_interwal.grid(row=1, column=1)
        self.interwal_var.trace_add("write", lambda *_: self.lbl_interwal.config(text=f"{self.interwal_var.get()} ms"))
        
        # Suwak liczby pięter
        tk.Label(ustawienia_frame, text="Liczba pięter", bg="#202124", fg="#cccccc", 
                font=("Segoe UI", 9)).grid(row=2, column=0, columnspan=2, pady=(10,2))
        self.scale_pietra = ttk.Scale(ustawienia_frame, from_=6, to=18, orient=tk.HORIZONTAL,
                                     variable=self.pietra_var, command=self._zmiana_pieter)
        self.scale_pietra.grid(row=3, column=0, sticky="ew", padx=(0,10))
        self.lbl_pietra = tk.Label(ustawienia_frame, text="10", bg="#202124", fg="white", 
                                   font=("Segoe UI", 9, "bold"), width=7)
        self.lbl_pietra.grid(row=3, column=1)
        self.pietra_var.trace_add("write", lambda *_: self.lbl_pietra.config(text=str(self.pietra_var.get())))
        
        ustawienia_frame.columnconfigure(0, weight=1)
        
        # --- 2. Layout główny (kontener na resztę interfejsu) ---
        self.main_container = tk.Frame(root, bg=self.kolor_tla)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        
        self.panel_zewnatrz = self._stworz_karte(self.main_container, "Zewnątrz (Wezwania)")
        self.panel_mapa = self._stworz_karte(self.main_container, "Mapa Szybu")
        
        self.canvas_wysokosc = 550
        self.canvas = tk.Canvas(self.panel_mapa, width=150, height=self.canvas_wysokosc, 
                                bg="#ffffff", bd=0, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.panel_kabina = self._stworz_karte(self.main_container, "Wnętrze Kabiny", bg_kolor="#e4e6eb")
        self.panel_info = self._stworz_karte(self.main_container, "Sterowanie i Stan")
        
        self._buduj_panel_zewnatrz()
        self._buduj_panel_kabiny()
        self._buduj_panel_info()
        self.odswiez_widok()

    def _stworz_karte(self, parent, tytul, bg_kolor="white"):
        kontener = tk.Frame(parent, bg=self.kolor_tla)
        kontener.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        tk.Label(kontener, text=tytul, bg=self.kolor_tla, fg="#444444", font=("Segoe UI", 11, "bold")).pack(pady=(0, 6), anchor="w")
        karta = tk.Frame(kontener, bg=bg_kolor, bd=0, highlightthickness=1, highlightbackground="#dcdfe6")
        karta.pack(fill=tk.BOTH, expand=True, ipadx=10, ipady=10)
        return karta

    def _czysc_panel(self, panel):
        """Usuwa wszystkie widgety z danego panelu."""
        for widget in panel.winfo_children():
            widget.destroy()

    def _buduj_panel_zewnatrz(self):
        self._czysc_panel(self.panel_zewnatrz)
        for i in reversed(range(self.parametry.liczba_pieter)):
            f = tk.Frame(self.panel_zewnatrz, bg="white")
            f.pack(pady=4)
            tk.Label(f, text=f"P{i:02d}", width=3, bg="white", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
            
            # Przycisk w górę
            btn_up = tk.Button(f, text="▲", command=lambda p=i: self.wezwij(p, Kierunek.GORA), 
                              relief=tk.FLAT, bg="#e8f0fe", font=("Arial", 10))
            btn_up.pack(side=tk.LEFT, padx=2)
            if i == self.parametry.liczba_pieter - 1:
                btn_up.config(state=tk.DISABLED, bg="#f8f9fa", fg="#cccccc")
            
            # Przycisk w dół
            btn_down = tk.Button(f, text="▼", command=lambda p=i: self.wezwij(p, Kierunek.DOL), 
                                relief=tk.FLAT, bg="#fce8e6", font=("Arial", 10))
            btn_down.pack(side=tk.LEFT, padx=2)
            if i == 0:
                btn_down.config(state=tk.DISABLED, bg="#f8f9fa", fg="#cccccc")

    def _buduj_panel_kabina_lcd(self):
        f_ekran = tk.Frame(self.panel_kabina, bg="#202124", padx=10, pady=5)
        f_ekran.pack(pady=10, fill=tk.X)
        self.ekran_pietro = tk.Label(f_ekran, text="0", font=("Consolas", 28), bg="#202124", fg="#ff5252")
        self.ekran_pietro.pack(side=tk.LEFT)
        self.ekran_kierunek = tk.Label(f_ekran, text="-", font=("Consolas", 28), bg="#202124", fg="#ff5252")
        self.ekran_kierunek.pack(side=tk.RIGHT)

    def _buduj_panel_kabiny(self):
        self._czysc_panel(self.panel_kabina)
        self._buduj_panel_kabina_lcd()
        f_guziki = tk.Frame(self.panel_kabina, bg="#e4e6eb")
        f_guziki.pack(pady=10)
        # Powrót do oryginalnego układu dwukolumnowego
        for i in reversed(range(self.parametry.liczba_pieter)):
            btn = OkraglyPrzycisk(f_guziki, str(i), lambda p=i: self.wybierz(p))
            row = (self.parametry.liczba_pieter - 1 - i) // 2
            col = (self.parametry.liczba_pieter - 1 - i) % 2
            btn.grid(row=row, column=col, padx=8, pady=8)

    def _buduj_panel_info(self):
        f_ctrl = tk.Frame(self.panel_info, bg="white")
        f_ctrl.pack(pady=10)
        
        # Przyciski sterowania
        tk.Button(f_ctrl, text="Krok +1", command=self.krok, bg="#e8eaed", relief=tk.FLAT, 
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)
        tk.Button(f_ctrl, text="Piętro +1", command=self.skok_pietro, bg="#d2e3fc", relief=tk.FLAT, 
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)
        
        self.btn_play = tk.Button(f_ctrl, text="Start", command=self.przelacz, bg="#81c995", fg="white", 
                                 relief=tk.FLAT, width=8, font=("Segoe UI", 9, "bold"))
        self.btn_play.pack(side=tk.LEFT, padx=2)
        tk.Button(f_ctrl, text="Reset", command=self.reset, bg="#f28b82", fg="white", relief=tk.FLAT, 
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)
        
        f_log = tk.Frame(self.panel_info, bg="#2b2d30")
        f_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        self.etykieta_stanu = tk.Label(f_log, text="", justify=tk.LEFT, font=("Consolas", 9), 
                                       bg="#2b2d30", fg="#a9b7c6", anchor="nw")
        self.etykieta_stanu.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # --- Obsługa zmian ustawień ---
    def _zmiana_interwalu(self, *args):
        nowy_interwal = self.interwal_var.get()
        self.interwal_ticku_ms = nowy_interwal
        # Jeśli symulacja działa, restartujemy pętlę z nowym interwałem
        if self.symulacja_dziala:
            if self.after_id:
                self.root.after_cancel(self.after_id)
            self.petla()

    def _zmiana_pieter(self, *args):
        nowa_liczba = self.pietra_var.get()
        if nowa_liczba == self.parametry.liczba_pieter:
            return
        
        # Zatrzymaj symulację
        self.symulacja_dziala = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.btn_play.config(text="Start", bg="#81c995")
        
        # Utwórz nowe parametry i windę
        self.parametry = ParametryWindy(liczba_pieter=nowa_liczba)
        self.winda = SilnikWindy(parametry=self.parametry)
        
        # Przebuduj interfejs zależny od liczby pięter
        self._buduj_panel_zewnatrz()
        self._buduj_panel_kabiny()
        self.odswiez_widok()

    # --- LOGIKA ---
    def skok_pietro(self):
        for _ in range(self.parametry.ticki_przejazdu_na_pietro):
            self.winda.krok()
        self.odswiez_widok()

    def krok(self): 
        self.winda.krok()
        self.odswiez_widok()

    def reset(self): 
        self.symulacja_dziala = False
        if self.after_id: 
            self.root.after_cancel(self.after_id)
        self.winda = SilnikWindy(self.parametry)
        self.btn_play.config(text="Start", bg="#81c995")
        self.odswiez_widok()

    def przelacz(self):
        self.symulacja_dziala = not self.symulacja_dziala
        self.btn_play.config(text="Stop" if self.symulacja_dziala else "Start", 
                             bg="#f28b82" if self.symulacja_dziala else "#81c995")
        if self.symulacja_dziala: 
            self.petla()

    def petla(self):
        if self.symulacja_dziala:
            self.winda.krok()
            self.odswiez_widok()
            self.after_id = self.root.after(self.interwal_ticku_ms, self.petla)

    def wezwij(self, p, k): 
        self.winda.dodaj_wezwanie_z_pietra_teraz(p, k, ZrodloZgloszenia.CZLOWIEK)
        self.odswiez_widok()

    def wybierz(self, p): 
        self.winda.dodaj_wybor_z_kabiny_teraz(p, ZrodloZgloszenia.CZLOWIEK)
        self.odswiez_widok()

    def _rysuj_zaokraglony_prostokat(self, x1, y1, x2, y2, promien=8, **kwargs):
        punkty = [x1+promien, y1, x1+promien, y1, x2-promien, y1, x2-promien, y1, x2, y1, x2, y1+promien, x2, y1+promien, x2, y2-promien, x2, y2-promien, x2, y2, x2-promien, y2, x2-promien, y2, x1+promien, y2, x1+promien, y2, x1, y2, x1, y2-promien, x1, y2-promien, x1, y1+promien, x1, y1+promien, x1, y1]
        return self.canvas.create_polygon(punkty, smooth=True, **kwargs)

    def odswiez_widok(self):
        stan = self.winda.snapshot()
        tick = self.winda.aktualny_tick
        
        # --- Aktualizacja zegara ---
        dane_czasu = self.czas_sym.tick_na_czas(tick)
        godz_str = f"{dane_czasu['godzina']:02d}:{dane_czasu['minuta']:02d}:{dane_czasu['sekunda']:02d}"
        self.lbl_zegar.config(text=godz_str)
        self.lbl_dzien.config(text=NAZWY_DNI_TYGODNIA[dane_czasu['dzien_tygodnia']].upper())
        
        # --- Bezpieczne formatowanie wezwań ---
        def bezpiecznie_formatuj_wezwania(zbior):
            if not zbior:
                return ""
            
            sformatowane_linie = []
            for element in zbior:
                nr_pietra = "?"
                zrodlo = "CZŁOWIEK"
                
                if isinstance(element, int):
                    nr_pietra = element
                elif isinstance(element, dict):
                    nr_pietra = element.get("pietro", "?")
                    zrodlo = str(element.get("zrodlo", "CZŁOWIEK")).split('.')[-1]
                elif hasattr(element, "pietro"):
                    nr_pietra = getattr(element, "pietro")
                    if hasattr(element, "zrodlo"):
                        zrodlo = str(getattr(element, "zrodlo")).split('.')[-1]
                elif isinstance(element, (list, tuple)):
                    nr_pietra = element[0]
                    if len(element) > 1:
                        zrodlo = str(element[1]).split('.')[-1]
                else:
                    nr_pietra = str(element)
                
                sformatowane_linie.append(f"[{nr_pietra}, {zrodlo}]")
            
            sformatowane_linie.sort()
            return "\n" + "\n".join(sformatowane_linie)

        self.etykieta_stanu.config(
            text=f"PIĘTRO: {stan['aktualne_pietro']}\n"
                 f"KIERUNEK: {stan['kierunek']}\n"
                 f"RUCH: {stan['czy_jedzie']}\n"
                 f"STOJI: {stan['czy_stoi_na_przystanku']}\n"
                 f"POZOSTAŁO TICKÓW: {stan['ticki_do_nastepnego_pietra']}\n\n"
                 f"WEZWANIA GÓRA: {bezpiecznie_formatuj_wezwania(stan['oczekujace'].get('wezwania_gora', []))}\n"
                 f"WEZWANIA DÓŁ: {bezpiecznie_formatuj_wezwania(stan['oczekujace'].get('wezwania_dol', []))}\n"
                 f"KABINA: {bezpiecznie_formatuj_wezwania(stan['oczekujace'].get('wybory_z_kabiny', []))}"
        )
        
        akt_p = stan["aktualne_pietro"]
        str_kier = str(stan["kierunek"]).split('.')[-1]
        
        # Płynna pozycja
        offset = 0
        if stan["czy_jedzie"] and self.parametry.ticki_przejazdu_na_pietro > 0:
            ulamek = 1.0 - (stan["ticki_do_nastepnego_pietra"] / self.parametry.ticki_przejazdu_na_pietro)
            offset = ulamek if str_kier == "GORA" else -ulamek

        self.ekran_pietro.config(text=str(akt_p))
        self.ekran_kierunek.config(text="▲" if str_kier == "GORA" else "▼" if str_kier == "DOL" else "-", 
                                   fg="#81c995" if str_kier == "GORA" else "#f28b82" if str_kier == "DOL" else "#7f8c8d")

        self.canvas.delete("all")
        h_p = self.canvas_wysokosc / self.parametry.liczba_pieter
        for i in range(self.parametry.liczba_pieter):
            y = self.canvas_wysokosc - (i * h_p)
            self.canvas.create_line(30, y, 150, y, fill="#e0e0e0", dash=(4, 4))
            self.canvas.create_text(15, y - 10, text=f"P{i}", font=("Segoe UI", 9, "bold"), fill="#aaaaaa")
        
        w_h = h_p * 0.8
        y_mid = self.canvas_wysokosc - ((akt_p + offset) * h_p) - (h_p/2)
        self._rysuj_zaokraglony_prostokat(50, y_mid - w_h/2, 120, y_mid + w_h/2, promien=8, 
                                          fill="#fbbc04" if stan["czy_stoi_na_przystanku"] else "#4285f4")

if __name__ == "__main__":
    root = tk.Tk()
    app = SymulatorWindyGUI(root)
    root.mainloop()