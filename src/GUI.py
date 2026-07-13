import tkinter as tk
from tkinter import ttk
from pathlib import Path

from Konfiguracja_windy import ParametryWindy
from Silnik_windy import SilnikWindy
from Kierunki_i_typy import Kierunek
from Czas_symulacji import CzasSymulacji, NAZWY_DNI_TYGODNIA
from Loader_planow import wczytaj_repozytorium_planow
from Menedzer_agentow import KonfiguracjaGrupyAgentow, MenedzerAgentow
from Model_energii import MonitorEnergiiWindy
from Logger_symulacji import LoggerSymulacji
from Ustawienia_projektu import UstawieniaProjektu


class SymulatorWindyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Symulator Inteligentnej Windy (z agentami)")
        self.kolor_tla = "#f0f2f5"
        self.root.configure(bg=self.kolor_tla)

        # --- STAŁE USTAWIENIA SYMULACJI ---
        self.LICZBA_PIETER = 15
        self.TICKI_PRZEJAZDU = 4
        self.TICKI_POSTOJU = 4
        self.MAX_POJEMNOSC = 6
        self.BAZOWY_INTERWAL_MS = 400  # bazowe opóźnienie dla prędkości 1x

        # --- INICJALIZACJA BACKENDU ---
        self.parametry = ParametryWindy(
            liczba_pieter=self.LICZBA_PIETER,
            pietro_startowe=0,
            ticki_przejazdu_na_pietro=self.TICKI_PRZEJAZDU,
            ticki_postoju=self.TICKI_POSTOJU,
            maks_pojemnosc=self.MAX_POJEMNOSC,
            poczatkowe_obciazenie=0,
        )
        self.winda = SilnikWindy(parametry=self.parametry)
        self.czas_sym = CzasSymulacji(dzien_tygodnia_startowy=0, sekunda_dnia_startowa=8 * 3600 + 30 * 60)

        # Wczytanie planów i utworzenie menedżera
        sciezka_planow = Path(__file__).resolve().parent.parent / "data" / "Plany_zajec"
        self.repozytorium = wczytaj_repozytorium_planow(sciezka_planow)
        self.ustawienia = UstawieniaProjektu()
        self.menedzer = MenedzerAgentow(self.repozytorium, self.winda, self.ustawienia)
        self._dodaj_grupy_agentow()

        self.monitor_energii = MonitorEnergiiWindy()
        self.logger = LoggerSymulacji(Path(__file__).resolve().parent.parent / "outputs" / "GUI_logs")

        # Stan symulacji
        self.symulacja_dziala = False
        self.after_id = None
        self.predkosc = 1.0  # mnożnik prędkości (1x, 2x, 5x, 10x)
        self.interwal_ms = self.BAZOWY_INTERWAL_MS  # aktualne opóźnienie

        # --- BUDOWA INTERFEJSU ---
        self._buduj_top_bar()
        self._buduj_pasek_sterowania()
        self._buduj_main_layout()
        self.odswiez_widok()

    def _dodaj_grupy_agentow(self):
        """Dodaje przykładowe grupy agentów (jak w konsoli)."""
        plan_ids = self.repozytorium.plan_ids()
        if not plan_ids:
            return
        grupy = [
            ("g1_p4", plan_ids[0], 4, 5),
            ("g2_p7", plan_ids[1 % len(plan_ids)], 7, 4),
            ("g3_p10", plan_ids[2 % len(plan_ids)], 10, 3),
        ]
        for nazwa, plan_id, pietro, liczba in grupy:
            self.menedzer.dodaj_grupe(KonfiguracjaGrupyAgentow(nazwa, plan_id, pietro, liczba))

    # ----------------------------------------------------------------------
    # BUDOWA ELEMENTÓW GUI
    # ----------------------------------------------------------------------
    def _buduj_top_bar(self):
        top_frame = tk.Frame(self.root, bg="#202124")
        top_frame.pack(side=tk.TOP, fill=tk.X)

        # Zegar
        self.panel_zegara = tk.Frame(top_frame, bg="#202124", pady=5)
        self.panel_zegara.pack(side=tk.LEFT, padx=20)
        self.lbl_zegar = tk.Label(self.panel_zegara, text="08:00:00", font=("Consolas", 28, "bold"),
                                  bg="#202124", fg="#ffffff")
        self.lbl_zegar.pack()
        self.lbl_dzien = tk.Label(self.panel_zegara, text="PONIEDZIAŁEK", font=("Segoe UI", 11, "bold"),
                                  bg="#202124", fg="#81c995")
        self.lbl_dzien.pack()

        # Przycisk Start/Stop
        self.btn_play = tk.Button(top_frame, text="Start", command=self.przelacz,
                                  bg="#81c995", fg="white", relief=tk.FLAT, width=10,
                                  font=("Segoe UI", 10, "bold"))
        self.btn_play.pack(side=tk.RIGHT, padx=20, pady=5)

        # Przycisk Reset
        btn_reset = tk.Button(top_frame, text="Reset", command=self.reset,
                              bg="#f28b82", fg="white", relief=tk.FLAT, width=10,
                              font=("Segoe UI", 10, "bold"))
        btn_reset.pack(side=tk.RIGHT, padx=10, pady=5)

    def _buduj_pasek_sterowania(self):
        """Dolny pasek z suwakiem prędkości i przyciskiem +15 min."""
        control_frame = tk.Frame(self.root, bg="#e8eaed", pady=5, padx=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # Suwak prędkości (od 0.5x do 20x, logarytmicznie)
        tk.Label(control_frame, text="Prędkość:", bg="#e8eaed", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_scale = ttk.Scale(control_frame, from_=0.5, to=20.0, orient=tk.HORIZONTAL,
                                     variable=self.speed_var, command=self._zmiana_predkosci)
        self.speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.lbl_predkosc = tk.Label(control_frame, text="1.0x", bg="#e8eaed", font=("Segoe UI", 9, "bold"), width=6)
        self.lbl_predkosc.pack(side=tk.LEFT, padx=5)

        # Przycisk "+15 min"
        btn_15min = tk.Button(control_frame, text="+15 min", command=lambda: self.skok_czasowy(15),
                              bg="#d2e3fc", relief=tk.FLAT, font=("Segoe UI", 9, "bold"))
        btn_15min.pack(side=tk.LEFT, padx=10)

        # Przycisk "+1 godzina" (opcjonalnie)
        btn_1h = tk.Button(control_frame, text="+1 h", command=lambda: self.skok_czasowy(60),
                           bg="#d2e3fc", relief=tk.FLAT, font=("Segoe UI", 9, "bold"))
        btn_1h.pack(side=tk.LEFT, padx=5)

        # Etykieta informująca o aktualnym interwale
        self.lbl_interwal = tk.Label(control_frame, text="400 ms", bg="#e8eaed", font=("Segoe UI", 9))
        self.lbl_interwal.pack(side=tk.RIGHT, padx=10)

    def _zmiana_predkosci(self, event=None):
        """Aktualizuje interwał na podstawie prędkości."""
        self.predkosc = self.speed_var.get()
        if self.predkosc < 0.5:
            self.predkosc = 0.5
        # Interwał = bazowy / prędkość, ale ograniczamy do min 10 ms i max 2000 ms
        self.interwal_ms = int(self.BAZOWY_INTERWAL_MS / self.predkosc)
        if self.interwal_ms < 10:
            self.interwal_ms = 10
        if self.interwal_ms > 2000:
            self.interwal_ms = 2000
        self.lbl_predkosc.config(text=f"{self.predkosc:.1f}x")
        self.lbl_interwal.config(text=f"{self.interwal_ms} ms")
        # Jeśli symulacja działa, restartujemy pętlę z nowym interwałem
        if self.symulacja_dziala and self.after_id:
            self.root.after_cancel(self.after_id)
            self.petla()

    def _stworz_karte(self, parent, tytul):
        kontener = tk.Frame(parent, bg=self.kolor_tla)
        # Tytuł
        tk.Label(kontener, text=tytul, bg=self.kolor_tla, fg="#444444",
             font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 4))
        # Karta (ramka właściwa)
        karta = tk.Frame(kontener, bg="white", bd=0, highlightthickness=1,
                     highlightbackground="#dcdfe6")
        karta.grid(row=1, column=0, sticky="nsew")
        kontener.rowconfigure(1, weight=1)
        kontener.columnconfigure(0, weight=1)
        return kontener, karta   # zwracamy kontener i kartę

    def _buduj_main_layout(self):
        self.main_container = tk.Frame(self.root, bg=self.kolor_tla)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 2 wiersze, 3 kolumny – równe wagi
        for col in range(3):
            self.main_container.columnconfigure(col, weight=1)
        for row in range(2):
            self.main_container.rowconfigure(row, weight=1)

        # ---- Wiersz 0 ----
        # Szyb
        self.panel_mapa, self.frame_mapa = self._stworz_karte(self.main_container, "Szyb windy")
        self.panel_mapa.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.canvas_wysokosc = 300
        self.canvas = tk.Canvas(self.frame_mapa, width=180, height=self.canvas_wysokosc,
                            bg="#ffffff", bd=0, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Kolejki
        self.panel_kolejki, self.frame_kolejki = self._stworz_karte(self.main_container, "Kolejki na piętrach")
        self.panel_kolejki.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        self.lista_kolejek = tk.Text(self.frame_kolejki, wrap=tk.NONE, font=("Consolas", 9),
                                 bg="#f8f9fa", fg="#333333", bd=0, highlightthickness=0)
        self.lista_kolejek.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll_k = tk.Scrollbar(self.frame_kolejki, command=self.lista_kolejek.yview)
        scroll_k.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista_kolejek.config(yscrollcommand=scroll_k.set)
        self.lista_kolejek.config(state=tk.DISABLED)

        # Pasażerowie
        self.panel_pasazerowie, self.frame_pasazerowie = self._stworz_karte(self.main_container, "Winda (pasażerowie)")
        self.panel_pasazerowie.grid(row=0, column=2, sticky="nsew", padx=4, pady=4)
        self.lista_pasazerow = tk.Text(self.frame_pasazerowie, wrap=tk.WORD, font=("Consolas", 9),
                                   bg="#f8f9fa", fg="#333333", bd=0, highlightthickness=0)
        self.lista_pasazerow.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll_p = tk.Scrollbar(self.frame_pasazerowie, command=self.lista_pasazerow.yview)
        scroll_p.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista_pasazerow.config(yscrollcommand=scroll_p.set)
        self.lista_pasazerow.config(state=tk.DISABLED)

        # ---- Wiersz 1 ----
        # Kolumna 0 pozostaje pusta (brak widgetu)

        # Planowane akcje (pod kolejkami)
        self.panel_akcje, self.frame_akcje = self._stworz_karte(self.main_container, "Planowane akcje agentów")
        self.panel_akcje.grid(row=1, column=1, sticky="nsew", padx=4, pady=4)
        self.lista_akcji = tk.Text(self.frame_akcje, wrap=tk.WORD, font=("Consolas", 9),
                               bg="#f8f9fa", fg="#333333", bd=0, highlightthickness=0)
        self.lista_akcji.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll_a = tk.Scrollbar(self.frame_akcje, command=self.lista_akcji.yview)
        scroll_a.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista_akcji.config(yscrollcommand=scroll_a.set)
        self.lista_akcji.config(state=tk.DISABLED)

        # Logi (pod pasażerami)
        self.panel_log, self.frame_log = self._stworz_karte(self.main_container, "Logi i podsumowanie")
        self.panel_log.grid(row=1, column=2, sticky="nsew", padx=4, pady=4)
        self.text_log = tk.Text(self.frame_log, wrap=tk.WORD, font=("Consolas", 9),
                            bg="#2b2d30", fg="#a9b7c6", bd=0, highlightthickness=0)
        self.text_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll_l = tk.Scrollbar(self.frame_log, command=self.text_log.yview)
        scroll_l.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_log.config(yscrollcommand=scroll_l.set)
        self.text_log.config(state=tk.DISABLED)

    # ----------------------------------------------------------------------
    # METODY STEROWANIA SYMULACJĄ
    # ----------------------------------------------------------------------
    def krok(self):
        """Wykonuje jeden krok symulacji (tick)."""
        if self.winda is None:
            return
        self.winda.krok()
        self.monitor_energii.krok(self.winda.snapshot())
        czas_info = self.czas_sym.tick_na_czas(self.winda.aktualny_tick)
        self.menedzer.krok(czas_info)
        self.logger.pobierz_nowe_zdarzenia_z_menedzera(self.menedzer)

        # Okresowe zapisywanie próbek (co minutę)
        if czas_info["sekunda"] == 0:
            self.logger.zapisz_probke(
                czas_info=czas_info,
                snapshot_windy=self.winda.snapshot(),
                snapshot_menedzera=self.menedzer.snapshot(),
                snapshot_energii=self.monitor_energii.snapshot(),
            )

        self.odswiez_widok()

    def skok_czasowy(self, minuty):
        """Przeskakuje symulację do przodu o zadaną liczbę minut."""
        if self.symulacja_dziala:
            # Zatrzymaj na czas skoku
            self.symulacja_dziala = False
            if self.after_id:
                self.root.after_cancel(self.after_id)
                self.after_id = None
            self.btn_play.config(text="Start", bg="#81c995")

        # Wykonuj kroki aż do osiągnięcia różnicy czasu
        cel_tick = self.winda.aktualny_tick
        # Obliczamy docelowy tick: dodajemy minuty * 60 * ? 
        # Niestety nie mamy odwrotnego mapowania tick->czas. Użyjemy pętli.
        # Będziemy wykonywać kroki i sprawdzać czas, aż różnica osiągnie minuty.
        start_czas = self.czas_sym.tick_na_czas(self.winda.aktualny_tick)
        start_sekunda = start_czas["godzina"]*3600 + start_czas["minuta"]*60 + start_czas["sekunda"]
        cel_sekunda = start_sekunda + minuty * 60

        # Wykonujemy kroki, aż przekroczymy cel
        max_krokow = 100000  # zabezpieczenie
        for _ in range(max_krokow):
            self.krok()  # wykonuje jeden tick i aktualizuje widok
            akt_czas = self.czas_sym.tick_na_czas(self.winda.aktualny_tick)
            akt_sekunda = akt_czas["godzina"]*3600 + akt_czas["minuta"]*60 + akt_czas["sekunda"]
            # Sprawdzamy, czy przekroczyliśmy cel (uwzględniając przejście przez północ)
            if akt_sekunda >= cel_sekunda:
                break
            # Ograniczenie, żeby nie zablokować GUI
            self.root.update_idletasks()

        # Aktualizacja widoku po skoku
        self.odswiez_widok()
        # Jeśli symulacja była wcześniej włączona, wznawiamy
        if self.symulacja_dziala_prev:
            self.symulacja_dziala = True
            self.btn_play.config(text="Stop", bg="#f28b82")
            self.petla()

    def reset(self):
        """Resetuje całą symulację do stanu początkowego."""
        self.symulacja_dziala = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.btn_play.config(text="Start", bg="#81c995")

        # Nowe obiekty
        self.parametry = ParametryWindy(
            liczba_pieter=self.LICZBA_PIETER,
            pietro_startowe=0,
            ticki_przejazdu_na_pietro=self.TICKI_PRZEJAZDU,
            ticki_postoju=self.TICKI_POSTOJU,
            maks_pojemnosc=self.MAX_POJEMNOSC,
            poczatkowe_obciazenie=0,
        )
        self.winda = SilnikWindy(parametry=self.parametry)
        self.czas_sym = CzasSymulacji(dzien_tygodnia_startowy=0, sekunda_dnia_startowa=8 * 3600 + 30 * 60)
        self.menedzer = MenedzerAgentow(self.repozytorium, self.winda, self.ustawienia)
        self._dodaj_grupy_agentow()
        self.monitor_energii = MonitorEnergiiWindy()
        self.logger = LoggerSymulacji(Path(__file__).resolve().parent.parent / "outputs" / "GUI_logs")

        self.odswiez_widok()

    def przelacz(self):
        """Start/Stop ciągłej symulacji."""
        self.symulacja_dziala = not self.symulacja_dziala
        self.btn_play.config(text="Stop" if self.symulacja_dziala else "Start",
                             bg="#f28b82" if self.symulacja_dziala else "#81c995")
        if self.symulacja_dziala:
            self.petla()

    def petla(self):
        """Pętla symulacji (wywoływana cyklicznie)."""
        if self.symulacja_dziala:
            self.krok()
            self.after_id = self.root.after(self.interwal_ms, self.petla)

    # ----------------------------------------------------------------------
    # ODŚWIEŻANIE WIDOKU
    # ----------------------------------------------------------------------
    def odswiez_widok(self):
        """Aktualizuje wszystkie elementy GUI na podstawie bieżącego stanu."""
        if self.winda is None:
            return

        # 1. Zegar
        tick = self.winda.aktualny_tick
        dane_czasu = self.czas_sym.tick_na_czas(tick)
        godz_str = f"{dane_czasu['godzina']:02d}:{dane_czasu['minuta']:02d}:{dane_czasu['sekunda']:02d}"
        self.lbl_zegar.config(text=godz_str)
        self.lbl_dzien.config(text=NAZWY_DNI_TYGODNIA[dane_czasu['dzien_tygodnia']].upper())

        # 2. Snapshoty
        stan_windy = self.winda.snapshot()
        stan_menedzera = self.menedzer.snapshot()
        stan_energii = self.monitor_energii.snapshot()

        # 3. Canvas (szyb)
        self._rysuj_szyb(stan_windy, stan_menedzera)

        # 4. Panel kolejek (tekst)
        self._aktualizuj_panel_kolejek(stan_menedzera)

        # 5. Panel pasażerów w windzie
        self._aktualizuj_panel_pasazerow(stan_menedzera)

        # 6. Panel planowanych akcji agentów
        self._aktualizuj_panel_akcji(stan_menedzera)

        # 7. Logi i podsumowanie
        self._aktualizuj_logi(dane_czasu, stan_windy, stan_menedzera, stan_energii)

    def _rysuj_szyb(self, stan_windy, stan_menedzera):
        self.canvas.delete("all")
        h_p = self.canvas_wysokosc / self.LICZBA_PIETER
        akt_p = stan_windy["aktualne_pietro"]
        str_kier = str(stan_windy["kierunek"]).split('.')[-1]

        # Płynna pozycja windy
        offset = 0
        if stan_windy["czy_jedzie"] and self.TICKI_PRZEJAZDU > 0:
            ulamek = 1.0 - (stan_windy["ticki_do_nastepnego_pietra"] / self.TICKI_PRZEJAZDU)
            offset = ulamek if str_kier == "GORA" else -ulamek

        # Rysowanie poziomych linii dla pięter
        for i in range(self.LICZBA_PIETER):
            y = self.canvas_wysokosc - (i * h_p)
            self.canvas.create_line(40, y, 170, y, fill="#e0e0e0", dash=(4, 4))
            self.canvas.create_text(25, y - 10, text=f"P{i}", font=("Segoe UI", 9, "bold"), fill="#aaaaaa")

            # Liczba oczekujących na tym piętrze
            kolejki = stan_menedzera["kolejki"]
            if str(i) in kolejki:
                gora = len(kolejki[str(i)]["gora"])
                dol = len(kolejki[str(i)]["dol"])
                if gora > 0 or dol > 0:
                    tekst = f"↑{gora} ↓{dol}"
                    self.canvas.create_text(55, y - 10, text=tekst, font=("Consolas", 8),
                                            fill="#d32f2f" if gora + dol > 0 else "#888888")

        # Rysowanie windy
        w_h = h_p * 0.75
        y_mid = self.canvas_wysokosc - ((akt_p + offset) * h_p) - (h_p / 2)
        x1, y1 = 60, y_mid - w_h / 2
        x2, y2 = 150, y_mid + w_h / 2
        self._rysuj_zaokraglony_prostokat(x1, y1, x2, y2, promien=8,
                                          fill="#fbbc04" if stan_windy["czy_stoi_na_przystanku"] else "#4285f4")

        # Wewnątrz windy: liczba pasażerów
        obc = stan_windy["obciazenie"]
        self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                                text=str(obc), font=("Consolas", 14, "bold"), fill="white")

    def _rysuj_zaokraglony_prostokat(self, x1, y1, x2, y2, promien=8, **kwargs):
        punkty = [
            x1 + promien, y1,
            x2 - promien, y1,
            x2, y1,
            x2, y1 + promien,
            x2, y2 - promien,
            x2, y2,
            x2 - promien, y2,
            x1 + promien, y2,
            x1, y2,
            x1, y2 - promien,
            x1, y1 + promien,
            x1, y1
        ]
        return self.canvas.create_polygon(punkty, smooth=True, **kwargs)

    def _aktualizuj_panel_kolejek(self, stan_menedzera):
        self.lista_kolejek.config(state=tk.NORMAL)
        self.lista_kolejek.delete(1.0, tk.END)
        kolejki = stan_menedzera["kolejki"]
        if not kolejki:
            self.lista_kolejek.insert(tk.END, "Brak oczekujących.\n")
        else:
            for pietro in sorted(kolejki.keys(), reverse=True):
                gora = kolejki[pietro]["gora"]
                dol = kolejki[pietro]["dol"]
                if not gora and not dol:
                    continue
                self.lista_kolejek.insert(tk.END, f"Piętro {pietro:2d}:  ↑ {len(gora):2d}  ↓ {len(dol):2d}\n")
                for agent_id in gora[:5]:
                    self.lista_kolejek.insert(tk.END, f"   {agent_id} (↑)\n")
                if len(gora) > 5:
                    self.lista_kolejek.insert(tk.END, f"   ... i {len(gora)-5} więcej\n")
                for agent_id in dol[:5]:
                    self.lista_kolejek.insert(tk.END, f"   {agent_id} (↓)\n")
                if len(dol) > 5:
                    self.lista_kolejek.insert(tk.END, f"   ... i {len(dol)-5} więcej\n")
        self.lista_kolejek.config(state=tk.DISABLED)

    def _aktualizuj_panel_pasazerow(self, stan_menedzera):
        self.lista_pasazerow.config(state=tk.NORMAL)
        self.lista_pasazerow.delete(1.0, tk.END)

        agenci = stan_menedzera.get("agenci", {})
        w_windzie = [aid for aid, a in agenci.items() if a.get("stan") == "JEDZIE_WINDA"]

        if not w_windzie:
            self.lista_pasazerow.insert(tk.END, "Winda pusta.\n")
        else:
            self.lista_pasazerow.insert(tk.END, f"Liczba pasażerów: {len(w_windzie)}\n")
            for agent_id in w_windzie[:10]:
                agent = agenci.get(agent_id, {})
                cel = agent.get("cel_pietro", "?")
                self.lista_pasazerow.insert(tk.END, f"  {agent_id} -> P{cel}\n")
            if len(w_windzie) > 10:
                self.lista_pasazerow.insert(tk.END, f"  ... i {len(w_windzie)-10} więcej\n")
        self.lista_pasazerow.config(state=tk.DISABLED)

    def _aktualizuj_panel_akcji(self, stan_menedzera):
        """Wyświetla najbliższe akcje agentów."""
        self.lista_akcji.config(state=tk.NORMAL)
        self.lista_akcji.delete(1.0, tk.END)

        agenci = stan_menedzera.get("agenci", {})
        # Sortuj agentów według pozycji w kolejce lub ID
        # Wybierz tylko tych, którzy mają zaplanowane akcje
        akcje_list = []
        for agent_id, agent in agenci.items():
            nastepne = agent.get("nastepne_akcje", [])
            if nastepne:
                for akcja in nastepne[:2]:  # max 2 akcje na agenta
                    czas = akcja.get("czas", "?")
                    typ = akcja.get("etykieta", akcja.get("typ_akcji", "?"))
                    cel = akcja.get("pietro_docelowe")
                    start = akcja.get("pietro_startowe_symulowane")
                    trasa = f" P{start}->P{cel}" if start is not None and cel is not None else ""
                    losowe = " [L]" if akcja.get("czy_losowe") else ""
                    akcje_list.append((czas, agent_id, f"{typ}{trasa}{losowe}"))

        if not akcje_list:
            self.lista_akcji.insert(tk.END, "Brak planowanych akcji.\n")
        else:
            # Sortuj po czasie
            akcje_list.sort(key=lambda x: x[0])
            for czas, agent_id, opis in akcje_list[:30]:  # ogranicz do 30 wpisów
                self.lista_akcji.insert(tk.END, f"{czas} | {agent_id}: {opis}\n")

        self.lista_akcji.config(state=tk.DISABLED)

    def _aktualizuj_logi(self, czas_info, stan_windy, stan_menedzera, stan_energii):
        self.text_log.config(state=tk.NORMAL)
        self.text_log.delete(1.0, tk.END)

        lines = []
        lines.append(f"=== {czas_info['nazwa_dnia']} {czas_info['czas_tekst']} (tick {czas_info['tick']}) ===")
        lines.append(f"Piętro: {stan_windy['aktualne_pietro']}  Kierunek: {stan_windy['kierunek']}")
        lines.append(f"Obciążenie: {stan_windy['obciazenie']}/{stan_windy['maks_pojemnosc']}")
        lines.append(f"Energia całk.: {stan_energii['energia_calkowita']:.2f} kWh")
        stats = stan_menedzera["statystyki"]
        lines.append(f"Wejścia: {stats['liczba_wejsc_do_windy']}  Wyjścia: {stats['liczba_wyjsc_z_windy']}")
        lines.append(f"Ghost calle: {stats['liczba_ghost_calli']}  Schody: {stats['liczba_rezygnacji_schody']}")
        zdarzenia = self.menedzer.ostatnie_zdarzenia(5)
        if zdarzenia:
            lines.append("\nOstatnie zdarzenia:")
            for ev in zdarzenia:
                typ = ev["typ"]
                payload = ev["payload"]
                if "agent" in payload:
                    lines.append(f"  {typ}: {payload['agent']}")
                else:
                    lines.append(f"  {typ}")
        self.text_log.insert(tk.END, "\n".join(lines))
        self.text_log.config(state=tk.DISABLED)
        self.text_log.see(tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = SymulatorWindyGUI(root)
    root.mainloop()