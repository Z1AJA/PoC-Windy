from _bootstrap_paths import ROOT  # noqa: F401
from pathlib import Path
import json
import random
import traceback
import unittest
import subprocess
import sys

from Czas_symulacji import CzasSymulacji
from Konfiguracja_windy import ParametryWindy
from Loader_planow import wczytaj_repozytorium_planow
from Menedzer_agentow import KonfiguracjaGrupyAgentow, MenedzerAgentow
from Silnik_windy import SilnikWindy
from Kierunki_i_typy import Kierunek, ZrodloZgloszenia
from Ustawienia_projektu import UstawieniaProjektu

REPORT_DIR = ROOT / "reports" / "turbo_test"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def add_random_direct_events(winda: SilnikWindy, rng: random.Random, liczba_pieter: int, prob=0.0015):
    events = []
    if rng.random() < prob:
        pietro = rng.randint(0, liczba_pieter - 1)
        if pietro == 0:
            kier = Kierunek.GORA
        elif pietro == liczba_pieter - 1:
            kier = Kierunek.DOL
        else:
            kier = Kierunek.GORA if rng.random() < 0.5 else Kierunek.DOL
        try:
            winda.dodaj_wezwanie_z_pietra_teraz(pietro, kier, ZrodloZgloszenia.CZLOWIEK)
            events.append({"typ": "manual_call", "pietro": pietro, "kierunek": kier.name})
        except Exception as exc:
            events.append({"typ": "blad_manual_call", "pietro": pietro, "kierunek": kier.name, "error": str(exc)})
    if rng.random() < prob / 2:
        dest = rng.randint(0, liczba_pieter - 1)
        try:
            winda.dodaj_wybor_z_kabiny_teraz(dest, ZrodloZgloszenia.CZLOWIEK)
            events.append({"typ": "manual_cabin", "dest": dest})
        except Exception as exc:
            events.append({"typ": "blad_manual_cabin", "dest": dest, "error": str(exc)})
    return events


def validate_state(winda: SilnikWindy, menedzer: MenedzerAgentow, tick: int):
    errs = []
    if not (0 <= winda.obciazenie <= winda.maks_pojemnosc):
        errs.append(f"tick {tick}: obciazenie poza zakresem {winda.obciazenie}/{winda.maks_pojemnosc}")

    # duplicates / consistency in cabin
    if len(menedzer.agenci_w_windzie) != len(set(menedzer.agenci_w_windzie)):
        errs.append(f"tick {tick}: duplikaty w agenci_w_windzie")
    if len(menedzer.agenci_w_windzie) != winda.obciazenie:
        errs.append(f"tick {tick}: obciazenie != len(agenci_w_windzie) ({winda.obciazenie} vs {len(menedzer.agenci_w_windzie)})")

    seen_queue = set()
    for pietro, data in menedzer.kolejki.kolejki.items():
        for kierunek in ("gora", "dol"):
            kolejka = data[kierunek]
            if len(kolejka) != len(set(kolejka)):
                errs.append(f"tick {tick}: duplikat w kolejce {pietro}/{kierunek}")
            for idx, agent_id in enumerate(kolejka, start=1):
                if agent_id in seen_queue:
                    errs.append(f"tick {tick}: agent {agent_id} w wielu kolejkach")
                seen_queue.add(agent_id)
                agent = menedzer.agenci[agent_id]
                if agent.pozycja_w_kolejce != idx:
                    errs.append(f"tick {tick}: zła pozycja w kolejce dla {agent_id} ({agent.pozycja_w_kolejce} != {idx})")
                if agent.kierunek_kolejki != kierunek:
                    errs.append(f"tick {tick}: zły kierunek kolejki dla {agent_id}")
                if agent_id in menedzer.agenci_w_windzie:
                    errs.append(f"tick {tick}: agent {agent_id} jednocześnie w kolejce i w windzie")

    for agent_id, agent in menedzer.agenci.items():
        if agent.aktualne_pietro is not None and not (0 <= agent.aktualne_pietro < winda.parametry.liczba_pieter):
            errs.append(f"tick {tick}: agent {agent_id} ma złe piętro {agent.aktualne_pietro}")
        in_windzie = agent_id in menedzer.agenci_w_windzie
        if in_windzie and agent.stan.name != "JEDZIE_WINDA":
            errs.append(f"tick {tick}: agent {agent_id} w windzie ale stan {agent.stan.name}")
        if (agent.pozycja_w_kolejce is None) != (agent.kierunek_kolejki is None):
            errs.append(f"tick {tick}: niespójne pola kolejki dla {agent_id}")
        if (agent.pozycja_w_kolejce is None) != (agent.tick_wejscia_do_kolejki is None):
            errs.append(f"tick {tick}: niespójny tick kolejki dla {agent_id}")
        if agent.stan.name == "JEDZIE_WINDA" and not in_windzie:
            errs.append(f"tick {tick}: agent {agent_id} ma stan JEDZIE_WINDA ale nie ma go w agenci_w_windzie")
        for rec in agent.historia_przejazdow[-10:]:
            for pole in ("czas_oczekiwania_tick", "czas_przejazdu_tick", "czas_calkowity_tick"):
                val = rec.get(pole)
                if val is not None and val < 0:
                    errs.append(f"tick {tick}: ujemny {pole} u {agent_id}")
    return errs


def build_manager(seed: int, floors: int, capacity: int, travel: int, stop: int, start_sec: int):
    repo = wczytaj_repozytorium_planow(ROOT / "data" / "Plany_zajec")
    ustawienia = UstawieniaProjektu(seed_glowny=seed)
    param = ParametryWindy(
        liczba_pieter=floors,
        pietro_startowe=0,
        ticki_przejazdu_na_pietro=travel,
        ticki_postoju=stop,
        maks_pojemnosc=capacity,
        poczatkowe_obciazenie=0,
    )
    winda = SilnikWindy(parametry=param)
    czas = CzasSymulacji(dzien_tygodnia_startowy=0, sekunda_dnia_startowa=start_sec)
    men = MenedzerAgentow(repo, winda, ustawienia)
    plan_ids = repo.plan_ids()
    grupy = [
        ("g1_p4", plan_ids[0], min(4, floors - 1), 8),
        ("g2_p7", plan_ids[1 % len(plan_ids)], min(7, floors - 1), 7),
        ("g3_p10", plan_ids[2 % len(plan_ids)], min(10, floors - 1), 6),
    ]
    for nazwa, pid, pietro, count in grupy:
        men.dodaj_grupe(KonfiguracjaGrupyAgentow(nazwa, pid, pietro, count))
    return repo, ustawienia, winda, czas, men


def run_scenario(name: str, seed: int, floors: int, capacity: int, travel: int, stop: int, start_sec: int, ticks: int):
    rng = random.Random(seed + 999)
    repo, ustawienia, winda, czas, men = build_manager(seed, floors, capacity, travel, stop, start_sec)
    errors = []
    sampled = []
    manual_events = []
    for _ in range(ticks):
        winda.krok()
        info = czas.tick_na_czas(winda.aktualny_tick)
        men.krok(info)
        manual_events.extend(add_random_direct_events(winda, rng, floors))
        errs = validate_state(winda, men, winda.aktualny_tick)
        if errs:
            errors.extend(errs)
            if len(errors) > 50:
                break
        if info["sekunda"] == 0 and info["minuta"] % 30 == 0:
            snap = men.snapshot()
            sampled.append({
                "czas": info["czas_tekst"],
                "dzien": info["nazwa_dnia"],
                "pietro_windy": winda.aktualne_pietro,
                "obciazenie": winda.obciazenie,
                "kolejki": snap["kolejki"],
                "metryki": snap["metryki_zbiorcze"],
            })
    return {
        "name": name,
        "seed": seed,
        "ticks": ticks,
        "errors": errors,
        "sampled": sampled[-10:],
        "manual_events_count": len(manual_events),
        "final_snapshot": men.snapshot(),
    }


def run_unit_tests():
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-p", "testy_*.py"]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main():
    scenarios = [
        ("normalny_dzien", 111, 15, 6, 4, 4, 7 * 3600 + 30 * 60, 36_000),
        ("ciasna_pojemnosc", 222, 15, 2, 4, 4, 7 * 3600 + 0 * 60, 30_000),
        ("wolna_winda", 333, 15, 6, 8, 5, 7 * 3600 + 30 * 60, 30_000),
        ("szybka_winda", 444, 12, 6, 2, 2, 7 * 3600 + 45 * 60, 24_000),
        ("wieczorny_start", 555, 15, 6, 4, 4, 15 * 3600, 24_000),
    ]
    results = []
    for args in scenarios:
        try:
            results.append(run_scenario(*args))
        except Exception:
            results.append({
                "name": args[0],
                "seed": args[1],
                "ticks": args[-1],
                "errors": ["EXCEPTION:\n" + traceback.format_exc()],
                "sampled": [],
                "manual_events_count": 0,
                "final_snapshot": {},
            })

    unit = run_unit_tests()
    total_errors = sum(len(r["errors"]) for r in results)

    report = {
        "unit_tests": unit,
        "scenarios": results,
        "total_errors": total_errors,
        "all_passed": (unit["returncode"] == 0 and total_errors == 0),
    }

    json_path = REPORT_DIR / "raport_turbo_test.json"
    txt_path = REPORT_DIR / "raport_turbo_test.txt"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("RAPORT TURBO TESTU")
    lines.append("=" * 60)
    lines.append(f"Testy jednostkowe returncode: {unit['returncode']}")
    lines.append(f"Wszystkie scenariusze bez błędów: {report['all_passed']}")
    lines.append(f"Suma błędów scenariuszy: {total_errors}")
    lines.append("")
    if unit["stdout"]:
        lines.append("=== STDOUT TESTÓW JEDNOSTKOWYCH ===")
        lines.append(unit["stdout"].rstrip())
        lines.append("")
    if unit["stderr"]:
        lines.append("=== STDERR TESTÓW JEDNOSTKOWYCH ===")
        lines.append(unit["stderr"].rstrip())
        lines.append("")
    for res in results:
        lines.append(f"--- SCENARIUSZ: {res['name']} ---")
        lines.append(f"seed={res['seed']} ticks={res['ticks']} manual_events={res['manual_events_count']}")
        if res["errors"]:
            lines.append("BŁĘDY:")
            lines.extend("  " + err for err in res["errors"][:20])
        else:
            lines.append("Brak błędów.")
        lines.append("Ostatnie próbki:")
        for s in res["sampled"][-5:]:
            lines.append(f"  {s['dzien']} {s['czas']} | P={s['pietro_windy']} | obc={s['obciazenie']} | metryki={s['metryki']}")
        lines.append("")
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    print(txt_path)
    print(json_path)
    print("ALL_PASSED=", report["all_passed"])


if __name__ == "__main__":
    main()
