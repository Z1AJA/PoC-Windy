from __future__ import annotations

import os
import shutil
from typing import Iterable


def wyczysc_ekran() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _przytnij(linia: str, szerokosc: int) -> str:
    if len(linia) <= szerokosc:
        return linia
    if szerokosc <= 1:
        return linia[:szerokosc]
    return linia[: max(0, szerokosc - 1)] + "…"


def _panel(tytul: str, linie: Iterable[str], szerokosc: int, wysokosc: int) -> list[str]:
    wew = max(10, szerokosc - 2)
    wynik = [f"┌{_przytnij(f' {tytul} ', wew):<{wew}}┐"]
    body = list(linie)
    body = body[: max(0, wysokosc - 2)]
    while len(body) < max(0, wysokosc - 2):
        body.append("")
    for linia in body:
        wynik.append(f"│{_przytnij(linia, wew):<{wew}}│")
    wynik.append(f"└{'─' * wew}┘")
    return wynik


def _polacz_poziomo(lewy: list[str], prawy: list[str], odstep: int = 2) -> list[str]:
    wysokosc = max(len(lewy), len(prawy))
    lewy = lewy + [" " * len(lewy[0])] * (wysokosc - len(lewy))
    prawy = prawy + [" " * len(prawy[0])] * (wysokosc - len(prawy))
    return [l + (" " * odstep) + p for l, p in zip(lewy, prawy)]


def renderuj_dashboard(
    czas_info: dict,
    snapshot_windy: dict,
    snapshot_menedzera: dict,
    zdarzenia: list[dict],
) -> str:
    szer = shutil.get_terminal_size((180, 55)).columns
    panel_w = max(60, (szer - 6) // 2)
    panel_h_top = 12
    panel_h_mid = 18
    panel_h_bottom = 14

    winda_linie = [
        f"Tick: {czas_info['tick']}",
        f"Czas: {czas_info['nazwa_dnia']} {czas_info['czas_tekst']}",
        f"Piętro: {snapshot_windy['aktualne_pietro']}",
        f"Kierunek: {snapshot_windy['kierunek']}",
        f"Jedzie: {snapshot_windy['czy_jedzie']}",
        f"Stoi: {snapshot_windy['czy_stoi_na_przystanku']}",
        f"Pojemność: {snapshot_windy['obciazenie']}/{snapshot_windy['maks_pojemnosc']}",
        f"Aktywne zgłoszenia: {snapshot_windy['liczba_aktywnych_zgloszen']}",
    ]

    kolejki_linie = []
    kolejki = snapshot_menedzera["kolejki"]
    if not kolejki:
        kolejki_linie.append("Brak kolejek.")
    else:
        for pietro in sorted(kolejki.keys(), reverse=True):
            gora = len(kolejki[pietro]["gora"])
            dol = len(kolejki[pietro]["dol"])
            if gora or dol:
                kolejki_linie.append(f"P{int(pietro):02d} | ↑ {gora} | ↓ {dol}")
        if not kolejki_linie:
            kolejki_linie.append("Brak oczekujących.")

    stany = snapshot_menedzera["stany_agentow"]
    stats = snapshot_menedzera["statystyki"]
    metryki = snapshot_menedzera["metryki_zbiorcze"]
    agenci_linie = [
        f"Liczba agentów: {snapshot_menedzera['liczba_agentow']}",
        f"W windzie: {snapshot_menedzera['liczba_agentow_w_windzie']}",
        "",
        "Stany agentów:",
    ]
    for nazwa, liczba in sorted(stany.items()):
        agenci_linie.append(f"- {nazwa}: {liczba}")
    agenci_linie.extend([
        "",
        "Statystyki:",
        f"- wezwania ludzkie (agenci): {stats['liczba_nacisniec_agentowych']}",
        f"- wejścia do windy: {stats['liczba_wejsc_do_windy']}",
        f"- wyjścia z windy: {stats['liczba_wyjsc_z_windy']}",
        f"- ghost calle: {stats['liczba_ghost_calli']}",
        f"- schody: {stats['liczba_rezygnacji_schody']}",
        "",
        "Metryki zbiorcze:",
        f"- przejazdy windą: {metryki['liczba_przejazdow_winda']}",
        f"- śr. czekanie tick: {metryki['sredni_czas_oczekiwania_tick']}",
        f"- śr. przejazd tick: {metryki['sredni_czas_przejazdu_tick']}",
    ])

    akcje_linie = []
    agenci = list(snapshot_menedzera["agenci"].values())
    agenci = sorted(
        agenci,
        key=lambda a: (
            0 if a["pozycja_w_kolejce"] is not None else 1,
            a["pozycja_w_kolejce"] if a["pozycja_w_kolejce"] is not None else 9999,
            a["id_agenta"],
        ),
    )
    for agent in agenci[:8]:
        akcje_linie.append(f"{agent['id_agenta']} | {agent['stan']} | P{agent['aktualne_pietro']}")
        for akcja in agent.get("nastepne_akcje", [])[:2]:
            znacznik = " [L]" if akcja.get("czy_losowe") else ""
            akcje_linie.append(f"  -> {akcja['czas']} | {akcja['typ_akcji']}{znacznik}")
    if not akcje_linie:
        akcje_linie.append("Brak agentów.")

    event_lines = []
    for event in zdarzenia[-10:]:
        typ = event["typ"]
        payload = event["payload"]
        if "agent" in payload:
            prefix = f"{typ}: {payload['agent']}"
        else:
            prefix = typ
        event_lines.append(f"{prefix} | {payload}")
    if not event_lines:
        event_lines.append("Brak zdarzeń.")

    top = _polacz_poziomo(
        _panel("Winda i czas", winda_linie, panel_w, panel_h_top),
        _panel("Kolejki", kolejki_linie, panel_w, panel_h_top),
    )
    middle = _polacz_poziomo(
        _panel("Agenci / statystyki / metryki", agenci_linie, panel_w, panel_h_mid),
        _panel("Najbliższe akcje agentów", akcje_linie, panel_w, panel_h_mid),
    )
    bottom = _panel("Zdarzenia systemu", event_lines, panel_w * 2 + 2, panel_h_bottom)

    return "\n".join(top + [""] + middle + [""] + bottom)
