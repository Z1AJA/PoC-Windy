import tkinter as tk
from tkinter import ttk

# Importy z backendu
from Konfiguracja_windy import ParametryWindy
from Silnik_windy import SilnikWindy
from Kierunki_i_typy import Kierunek, ZrodloZgloszenia
from Czas_symulacji import CzasSymulacji, NAZWY_DNI_TYGODNIA

class SymulatorWindyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Symulator Inteligentnej Windy (4 Panele)")
        self.root.configure(bg="#e0e0e0")
        
        # --- 1. Inicjalizacja Backendu ---
        self.parametry = ParametryWindy(
            liczba_pieter=10,
            pietro_startowe=0,
            ticki_przejazdu_na_pietro=4, # Ustawione na 4 dla lepszej widoczności ułamków trasy
            ticki_postoju=2,
            maks_pojemnosc=8,
            poczatkowe_obciazenie=0
        )
        self.winda = SilnikWindy(parametry=self.parametry)
        
        # Inicjalizacja czasu symulacji (start w poniedziałek o 8:00:00)
        self.czas_sym = CzasSymulacji(
            dzien_tygodnia_startowy=0, 
            sekunda_dnia_startowa=8 * 3600 
        )
        
        self.symulacja_dziala = False
        self.interwal_ticku_ms = 400
        
        # --- 2. Tworzenie 4 Paneli ---
        
        # PANEL 1: Zewnątrz (Piętra i wezwania)
        self.panel_zewnatrz = tk.LabelFrame(root, text=" Zewnątrz (Wezwania) ", bg="white", font=("Arial", 10, "bold"))
        self.panel_zewnatrz.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        # PANEL 2: Szyb windy (Mapa)
        self.panel_mapa = tk.LabelFrame(root, text=" Mapa Szybu ", bg="white", font=("Arial", 10, "bold"))
        self.panel_mapa.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.canvas_wysokosc = 550
        self.canvas = tk.Canvas(self.panel_mapa, width=150, height=self.canvas_wysokosc, bg="lightgray")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # PANEL 3: Kabina (Wzorowane na zdjęciu)
        self.panel_kabina = tk.LabelFrame(root, text=" Wnętrze Kabiny ", bg="#b0b0b0", font=("Arial", 10, "bold"))
        self.panel_kabina.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        # PANEL 4: Informacje i Czas
        self.panel_info = tk.LabelFrame(root, text=" Czas i Informacje ", bg="white", font=("Arial", 10, "bold"))
        self.panel_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Budowanie wnętrza paneli
        self._buduj_panel_zewnatrz()
        self._buduj_panel_kabiny()
        self._buduj_panel_info()
        
        # Pierwsze odświeżenie
        self.odswiez_widok()

    def _buduj_panel_zewnatrz(self):
        for i in reversed(range(self.parametry.liczba_pieter)):
            f_zewn = tk.Frame(self.panel_zewnatrz, bg="white")
            f_zewn.pack(pady=4, padx=5)
            tk.Label(f_zewn, text=f"P {i:02d} ", width=4, bg="white", font=("Courier", 10, "bold")).pack(side=tk.LEFT)
            
            btn_up = tk.Button(f_zewn, text="▲", width=2, bg="#e0e0e0",
                               command=lambda p=i: self.wezwij_z_pietra(p, Kierunek.GORA))
            btn_up.pack(side=tk.LEFT, padx=1)
            if i == self.parametry.liczba_pieter - 1: btn_up.config(state=tk.DISABLED)
            
            btn_down = tk.Button(f_zewn, text="▼", width=2, bg="#e0e0e0",
                                 command=lambda p=i: self.wezwij_z_pietra(p, Kierunek.DOL))
            btn_down.pack(side=tk.LEFT, padx=1)
            if i == 0: btn_down.config(state=tk.DISABLED)

    def _buduj_panel_kabiny(self):
        # 3.1 Wyświetlacz (czarne tło, czerwony tekst)
        f_ekran = tk.Frame(self.panel_kabina, bg="black", bd=4, relief=tk.SUNKEN)
        f_ekran.pack(pady=15, padx=15, fill=tk.X)
        
        self.ekran_pietro = tk.Label(f_ekran, text="0", font=("Courier", 26, "bold"), bg="black", fg="red")
        self.ekran_pietro.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.ekran_kierunek = tk.Label(f_ekran, text="-", font=("Courier", 26, "bold"), bg="black", fg="red")
        self.ekran_kierunek.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # 3.2 Guziki (Siatka / Grid)
        f_guziki = tk.Frame(self.panel_kabina, bg="#b0b0b0")
        f_guziki.pack(pady=10)
        
        # Ułożenie w 2 kolumnach dla realizmu
        for i in reversed(range(self.parametry.liczba_pieter)):
            indeks_od_gory = self.parametry.liczba_pieter - 1 - i
            wiersz = indeks_od_gory // 2
            kolumna = indeks_od_gory % 2
            
            btn = tk.Button(f_guziki, text=str(i), font=("Arial", 14, "bold"), width=3, height=1, 
                            relief=tk.RAISED, bd=3, bg="#dcdcdc", activebackground="lightblue",
                            command=lambda p=i: self.wybierz_wewnatrz(p))
            btn.grid(row=wiersz, column=kolumna, padx=8, pady=8)

    def _buduj_panel_info(self):
        # Sekcja czasu symulacji
        self.etykieta_czasu = tk.Label(self.panel_info, text="Czas: --:--:--\nDzień: ---", 
                                       font=("Arial", 14, "bold"), bg="#303030", fg="yellow", bd=4, relief=tk.SUNKEN)
        self.etykieta_czasu.pack(fill=tk.X, padx=10, pady=10)
        
        # Kontrola
        f_kontrola = tk.Frame(self.panel_info, bg="white")
        f_kontrola.pack(pady=5)
        
        self.btn_krok = tk.Button(f_kontrola, text="Krok +1", command=self.wykonaj_krok_recznie, width=10)
        self.btn_krok.pack(side=tk.LEFT, padx=5)
        
        self.btn_play = tk.Button(f_kontrola, text="Start Symulacji", command=self.przelacz_symulacje, width=12, bg="lightgreen")
        self.btn_play.pack(side=tk.LEFT, padx=5)
        
        # Log stanu
        tk.Label(self.panel_info, text="Szczegóły stanu:", bg="white", font=("Arial", 10, "bold")).pack(pady=5)
        self.etykieta_stanu = tk.Label(self.panel_info, text="", justify=tk.LEFT, font=("Courier", 10), bg="black", fg="lime", anchor="nw")
        self.etykieta_stanu.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    # --- KOMUNIKACJA Z SILNIKIEM ---
    def wezwij_z_pietra(self, pietro, kierunek):
        self.winda.dodaj_wezwanie_z_pietra_teraz(pietro, kierunek, ZrodloZgloszenia.CZLOWIEK)
        self.odswiez_widok()

    def wybierz_wewnatrz(self, pietro):
        self.winda.dodaj_wybor_z_kabiny_teraz(pietro, ZrodloZgloszenia.CZLOWIEK)
        self.odswiez_widok()

    def wykonaj_krok_recznie(self):
        self.winda.krok()
        self.odswiez_widok()

    def przelacz_symulacje(self):
        if self.symulacja_dziala:
            self.symulacja_dziala = False
            self.btn_play.config(text="Start Symulacji", bg="lightgreen")
        else:
            self.symulacja_dziala = True
            self.btn_play.config(text="Stop Symulacji", bg="salmon")
            self.petla_symulacji()

    def petla_symulacji(self):
        if self.symulacja_dziala:
            self.winda.krok()
            self.odswiez_widok()
            self.root.after(self.interwal_ticku_ms, self.petla_symulacji)

    # --- WIZUALIZACJA ---
    def odswiez_widok(self):
        stan = self.winda.snapshot()
        
        # 1. Czas Symulacji
        aktualny_tick = stan.get("aktualny_tick", 0)
        dane_czasu = self.czas_sym.tick_na_czas(aktualny_tick)
        dzien_nazwa = NAZWY_DNI_TYGODNIA[dane_czasu["dzien_tygodnia"]]
        godzina = dane_czasu["godzina"]
        minuta = dane_czasu["minuta"]
        sekunda = dane_czasu["sekunda"]
        
        self.etykieta_czasu.config(
            text=f"Tick: {aktualny_tick}\nCzas: {godzina:02d}:{minuta:02d}:{sekunda:02d}\nDzień: {dzien_nazwa.capitalize()}"
        )
        
        # 2. Log Tekstowy
        tekst_stanu = (
            f"Fizyczne Piętro: {stan.get('aktualne_pietro', '?')}\n"
            f"Kierunek: {stan.get('kierunek', '?')}\n"
            f"W ruchu: {'Tak' if stan.get('czy_jedzie') else 'Nie'}\n"
            f"Na przystanku: {'Tak' if stan.get('czy_stoi_na_przystanku') else 'Nie'}\n"
            f"Ticki do celu: {stan.get('ticki_do_nastepnego_pietra', 0)}\n"
            f"Ticki postoju: {stan.get('ticki_postoju_pozostale', 0)}\n\n"
            f"Góra: {stan.get('oczekujace', {}).get('wezwania_gora', [])}\n"
            f"Dół:  {stan.get('oczekujace', {}).get('wezwania_dol', [])}\n"
            f"Kabina: {stan.get('oczekujace', {}).get('wybory_z_kabiny', [])}"
        )
        self.etykieta_stanu.config(text=tekst_stanu)
        
        # 3. Zmienne do wizualizacji i ekranu
        akt_pietro = stan.get("aktualne_pietro", 0)
        czy_jedzie = stan.get("czy_jedzie", False)
        ticki_do_celu = stan.get("ticki_do_nastepnego_pietra", 0)
        ticki_przejazdu = self.parametry.ticki_przejazdu_na_pietro
        kierunek = stan.get("kierunek")
        
        str_kierunek = str(kierunek).split('.')[-1]
        
        # Obliczanie pozycji "płynnej" dla mapy szybu
        offset_pietra = 0
        if czy_jedzie and ticki_przejazdu > 0:
            ulamek = 1.0 - (ticki_do_celu / ticki_przejazdu)
            if str_kierunek == "GORA": offset_pietra = ulamek
            elif str_kierunek == "DOL": offset_pietra = -ulamek

        # --- 4. Aktualizacja Panelu Kabiny (Wzorowane na zdjęciu) ---
        # Ustalanie piętra "najbliższego" dla wyświetlacza w kabinie
        najblizsze_pietro = akt_pietro
        if czy_jedzie and ticki_przejazdu > 0:
            przebyty_ulamek = 1.0 - (ticki_do_celu / ticki_przejazdu)
            if przebyty_ulamek >= 0.5: # Jesteśmy bliżej następnego piętra
                if str_kierunek == "GORA": najblizsze_pietro = akt_pietro + 1
                elif str_kierunek == "DOL": najblizsze_pietro = akt_pietro - 1

        self.ekran_pietro.config(text=str(najblizsze_pietro))
        
        if str_kierunek == "GORA": self.ekran_kierunek.config(text="▲", fg="lime")
        elif str_kierunek == "DOL": self.ekran_kierunek.config(text="▼", fg="red")
        else: self.ekran_kierunek.config(text="-", fg="gray") # BEZRUCH

        # --- 5. Rysowanie Mapy Szybu ---
        self.canvas.delete("all")
        liczba_pieter = self.parametry.liczba_pieter
        wysokosc_pietra = self.canvas_wysokosc / liczba_pieter
        
        for i in range(liczba_pieter):
            y = self.canvas_wysokosc - (i * wysokosc_pietra)
            self.canvas.create_line(0, y, 150, y, fill="gray", dash=(2, 2))
            self.canvas.create_text(15, y - 10, text=f"P {i}", anchor="w", font=("Arial", 8))
        
        winda_szer = 70
        winda_wys = wysokosc_pietra * 0.8
        winda_poziom = akt_pietro + offset_pietra
        
        dol_y = self.canvas_wysokosc - (winda_poziom * wysokosc_pietra)
        gora_y = dol_y - winda_wys
        lewo_x = (150 - winda_szer) / 2
        prawo_x = lewo_x + winda_szer
        
        kolor_windy = "gold" if stan.get("czy_stoi_na_przystanku") else "dodgerblue"
        self.canvas.create_rectangle(lewo_x, gora_y, prawo_x, dol_y, fill=kolor_windy, outline="black", width=2)
        
        # Znak na windzie na mapie
        znak_mapa = "-"
        if str_kierunek == "GORA": znak_mapa = "▲"
        if str_kierunek == "DOL": znak_mapa = "▼"
        self.canvas.create_text(lewo_x + winda_szer/2, gora_y + winda_wys/2, text=znak_mapa, font=("Arial", 16, "bold"))


if __name__ == "__main__":
    root = tk.Tk()
    app = SymulatorWindyGUI(root)
    root.mainloop()