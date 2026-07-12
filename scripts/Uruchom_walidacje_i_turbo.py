from _bootstrap_paths import *  # noqa: F401,F403

import json
from pathlib import Path

from Czas_symulacji import CzasSymulacji
from Konfiguracja_windy import ParametryWindy
from Loader_planow import wczytaj_repozytorium_planow
from Menedzer_agentow import KonfiguracjaGrupyAgentow, MenedzerAgentow
from Nawigacja_po_planie import zbuduj_harmonogram_przejazdow_agenta
from Silnik_windy import SilnikWindy
from Ustawienia_projektu import UstawieniaProjektu


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / 'outputs' / 'walidacja_turbo'
    out_dir.mkdir(parents=True, exist_ok=True)

    repo = wczytaj_repozytorium_planow(root / 'data' / 'Plany_zajec')
    ustawienia = UstawieniaProjektu(
        seed_glowny=12345,
        prawdopodobienstwo_losowego_cyklu_dnia=1.0,
        minimalna_liczba_losowych_cykli=1,
        maksymalna_liczba_losowych_cykli=2,
        prawdopodobienstwo_losowego_przejazdu_wewnatrz_akademika=1.0,
        minimalna_liczba_przejazdow_wewnatrz=1,
        maksymalna_liczba_przejazdow_wewnatrz=2,
    )

    wymagane_eventy = {
        'wyjscie_z_akademika', 'powrot_do_akademika',
        'przejazd_miedzy_pietrami', 'powrot_na_pietro_domowe'
    }
    znalezione_eventy = set()

    # Faza 1: wielokrotne losowanie planów agentów
    for plan_id in repo.plan_ids():
        plan = repo.pobierz(plan_id)
        for dzien in [d.dzien for d in plan.dni]:
            for seed in range(50):
                _, akcje = zbuduj_harmonogram_przejazdow_agenta(
                    plan=plan, dzien=dzien, generator=__import__('random').Random(seed),
                    bufor_wyjscia_przed_zajeciami_minuty=ustawienia.bufor_wyjscia_przed_zajeciami_minuty,
                    prog_powrotu_do_akademika_minuty=ustawienia.prog_powrotu_do_akademika_minuty,
                    prawdopodobienstwo_losowego_cyklu_dnia=ustawienia.prawdopodobienstwo_losowego_cyklu_dnia,
                    minimalna_liczba_losowych_cykli=ustawienia.minimalna_liczba_losowych_cykli,
                    maksymalna_liczba_losowych_cykli=ustawienia.maksymalna_liczba_losowych_cykli,
                    min_czas_poza_akademikiem_minuty=ustawienia.min_czas_poza_akademikiem_minuty,
                    max_czas_poza_akademikiem_minuty=ustawienia.max_czas_poza_akademikiem_minuty,
                    prawdopodobienstwo_losowego_przejazdu_wewnatrz_akademika=ustawienia.prawdopodobienstwo_losowego_przejazdu_wewnatrz_akademika,
                    minimalna_liczba_przejazdow_wewnatrz=ustawienia.minimalna_liczba_przejazdow_wewnatrz,
                    maksymalna_liczba_przejazdow_wewnatrz=ustawienia.maksymalna_liczba_przejazdow_wewnatrz,
                    min_czas_na_innym_pietrze_minuty=ustawienia.min_czas_na_innym_pietrze_minuty,
                    max_czas_na_innym_pietrze_minuty=ustawienia.max_czas_na_innym_pietrze_minuty,
                    najwczesniejsza_minuta_losowych_akcji=ustawienia.najwczesniejsza_minuta_losowych_akcji,
                    najpozniejsza_minuta_losowych_akcji=ustawienia.najpozniejsza_minuta_losowych_akcji,
                    minimalny_odstep_od_innych_akcji_minuty=ustawienia.minimalny_odstep_od_innych_akcji_minuty,
                    pietro_domowe=4,
                    minimalne_pietro_losowych_przejazdow_wewnatrz=ustawienia.minimalne_pietro_losowych_przejazdow_wewnatrz,
                    maksymalne_pietro_losowych_przejazdow_wewnatrz=ustawienia.maksymalne_pietro_losowych_przejazdow_wewnatrz,
                    pietro_parteru=ustawienia.pietro_parteru,
                )
                znalezione_eventy.update(a.typ_akcji for a in akcje if a.czy_losowe)

    # Faza 2: długi test stabilności
    winda = SilnikWindy(parametry=ParametryWindy(liczba_pieter=15, pietro_startowe=0, ticki_przejazdu_na_pietro=4, ticki_postoju=4, maks_pojemnosc=6, poczatkowe_obciazenie=0))
    menedzer = MenedzerAgentow(repo, winda, ustawienia)
    plan_ids = repo.plan_ids()
    grupy = [(4,8), (7,7), (10,6), (13,5)]
    for idx, (pietro, liczba) in enumerate(grupy):
        menedzer.dodaj_grupe(KonfiguracjaGrupyAgentow(f'g{idx+1}_p{pietro}', plan_ids[idx % len(plan_ids)], pietro, liczba))

    czas = CzasSymulacji(dzien_tygodnia_startowy=0, sekunda_dnia_startowa=7 * 3600)
    errors = []
    rekordy_ml = []
    last_log_idx = 0
    losowe_wykonane = set()

    for _ in range(100000):
        winda.krok()
        info = czas.tick_na_czas(winda.aktualny_tick)
        menedzer.krok(info)

        logs = list(menedzer.log_zdarzen)
        for event in logs[last_log_idx:]:
            payload = event['payload']
            if event['typ'] == 'akcja_agenta' and payload.get('czy_losowe'):
                losowe_wykonane.add(payload.get('akcja'))
            if event['typ'] in {'nacisniecie_przycisku_wezwania', 'nacisniecie_przycisku_kabiny'}:
                rekordy_ml.append({
                    'tick': payload.get('tick'),
                    'nazwa_dnia': info['nazwa_dnia'],
                    'czas_tekst': info['czas_tekst'],
                    'typ_nacisniecia': 'wezwanie_z_pietra' if event['typ']=='nacisniecie_przycisku_wezwania' else 'wybor_z_kabiny',
                    'pietro': payload.get('pietro', payload.get('cel')),
                    'kierunek': payload.get('kierunek', 'brak'),
                    'obciazenie_windy': winda.obciazenie,
                })
        last_log_idx = len(logs)

        ids_w_windzie = list(menedzer.agenci_w_windzie)
        if len(ids_w_windzie) != len(set(ids_w_windzie)):
            errors.append(f'tick {winda.aktualny_tick}: duplikat w agenci_w_windzie')

        seen_queue = set()
        snap_q = menedzer.kolejki.snapshot()
        for pietro, data in snap_q.items():
            for kierunek in ('gora','dol'):
                for aid in data[kierunek]:
                    key = (aid, pietro, kierunek)
                    if key in seen_queue:
                        errors.append(f'tick {winda.aktualny_tick}: duplikat w kolejce {key}')
                    seen_queue.add(key)

        for aid, agent in menedzer.agenci.items():
            if aid in menedzer.agenci_w_windzie and agent.stan.name != 'JEDZIE_WINDA':
                errors.append(f'tick {winda.aktualny_tick}: agent {aid} w windzie ale stan {agent.stan.name}')
            if agent.stan.name == 'JEDZIE_WINDA' and aid not in menedzer.agenci_w_windzie:
                errors.append(f'tick {winda.aktualny_tick}: agent {aid} stan JEDZIE_WINDA ale brak w agenci_w_windzie')
            if agent.czy_czeka_w_kolejce and agent.stan.name not in {'CZEKA_NA_WINDE_W_DOL','CZEKA_NA_WINDE_W_GORE'}:
                errors.append(f'tick {winda.aktualny_tick}: agent {aid} ma kolejkę ale stan {agent.stan.name}')
            for rec in agent.historia_przejazdow[-5:]:
                for pole in ('czas_oczekiwania_tick','czas_przejazdu_tick','czas_calkowity_tick'):
                    if rec.get(pole) is not None and rec[pole] < 0:
                        errors.append(f'tick {winda.aktualny_tick}: agent {aid} ma ujemne {pole}')
        if len(errors) > 100:
            break

    dziury_ml = []
    for idx, rec in enumerate(rekordy_ml):
        for key in ('tick','nazwa_dnia','czas_tekst','typ_nacisniecia','pietro','kierunek','obciazenie_windy'):
            if key not in rec or rec[key] is None:
                dziury_ml.append(f'rekord {idx}: brak {key}')
        if rec.get('obciazenie_windy',0) < 0:
            dziury_ml.append(f'rekord {idx}: ujemne obciazenie')

    raport = {
        'pokrycie_eventow_losowych_generowanych': sorted(znalezione_eventy),
        'brakujace_eventy_losowe_generowane': sorted(list(wymagane_eventy - znalezione_eventy)),
        'eventy_losowe_wykonane_w_turbo': sorted(losowe_wykonane),
        'liczba_rekordow_ml': len(rekordy_ml),
        'liczba_bledow_spojnosci': len(errors),
        'liczba_bledow_datasetu_ml': len(dziury_ml),
        'bledy_spojnosci_pierwsze_50': errors[:50],
        'bledy_datasetu_ml_pierwsze_50': dziury_ml[:50],
        'statystyki': menedzer.snapshot()['statystyki'],
        'metryki_zbiorcze': menedzer.snapshot()['metryki_zbiorcze'],
        'werdykt': 'OK' if not errors and not dziury_ml and not (wymagane_eventy - znalezione_eventy) else 'BLAD',
    }

    (out_dir / 'raport_walidacja_i_turbo.json').write_text(json.dumps(raport, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = [
        'RAPORT WALIDACJI I TURBO TESTU',
        '',
        f"Werdykt: {raport['werdykt']}",
        f"Pokrycie eventów generowanych: {raport['pokrycie_eventow_losowych_generowanych']}",
        f"Eventy losowe wykonane w turbo: {raport['eventy_losowe_wykonane_w_turbo']}",
        f"Liczba rekordów ML: {raport['liczba_rekordow_ml']}",
        f"Liczba błędów spójności: {raport['liczba_bledow_spojnosci']}",
        f"Liczba błędów datasetu ML: {raport['liczba_bledow_datasetu_ml']}",
        '',
        'Pierwsze błędy spójności:',
        *[f' - {x}' for x in errors[:20]],
        '',
        'Pierwsze błędy datasetu ML:',
        *[f' - {x}' for x in dziury_ml[:20]],
    ]
    (out_dir / 'raport_walidacja_i_turbo.txt').write_text('\n'.join(lines), encoding='utf-8')
    (out_dir / 'rekordy_ml_obserwowalne.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rekordy_ml), encoding='utf-8')
    print((out_dir / 'raport_walidacja_i_turbo.txt').read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
