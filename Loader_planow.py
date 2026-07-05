from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from Modele_planow import BlokZajec, DzienPlanu, PlanZajec


@dataclass(slots=True)
class RepozytoriumPlanow:
    plany: dict[str, PlanZajec]

    def plan_ids(self) -> list[str]:
        return sorted(self.plany.keys())

    def pobierz(self, plan_id: str) -> PlanZajec:
        try:
            return self.plany[plan_id]
        except KeyError as exc:
            raise KeyError(f"Nie znaleziono planu o id={plan_id!r}") from exc


def _wczytaj_plan_z_dict(dane: dict) -> PlanZajec:
    dni = []
    for dzien in dane.get("dni", []):
        bloki = []
        for blok in dzien.get("bloki", []):
            bloki.append(
                BlokZajec(
                    godzina_od=blok["godzina_od"],
                    godzina_do=blok["godzina_do"],
                    nazwa=blok["nazwa"],
                    wspolczynnik_uczestnictwa=float(blok["wspolczynnik_uczestnictwa"]),
                )
            )
        dni.append(DzienPlanu(dzien=dzien["dzien"], bloki=tuple(bloki)))

    return PlanZajec(
        plan_id=dane["plan_id"],
        rok=int(dane["rok"]),
        grupa=int(dane["grupa"]),
        wariant_zrodlowy=str(dane.get("wariant_zrodlowy", "")),
        dni=tuple(dni),
    )


def wczytaj_repozytorium_planow(sciezka: str | Path) -> RepozytoriumPlanow:
    sciezka = Path(sciezka)

    if not sciezka.exists():
        raise FileNotFoundError(f"Nie znaleziono sciezki: {sciezka}")

    plany: dict[str, PlanZajec] = {}

    if sciezka.is_dir():
        pliki = sorted(sciezka.glob("*.json"))
        for plik in pliki:
            dane = json.loads(plik.read_text(encoding="utf-8"))
            plan = _wczytaj_plan_z_dict(dane)
            plany[plan.plan_id] = plan
        return RepozytoriumPlanow(plany=plany)

    if sciezka.suffix.lower() == ".zip":
        with ZipFile(sciezka, "r") as archiwum:
            nazwy = sorted(
                nazwa for nazwa in archiwum.namelist()
                if nazwa.lower().endswith(".json")
            )
            for nazwa in nazwy:
                with archiwum.open(nazwa) as plik:
                    dane = json.loads(plik.read().decode("utf-8"))
                plan = _wczytaj_plan_z_dict(dane)
                plany[plan.plan_id] = plan
        return RepozytoriumPlanow(plany=plany)

    raise ValueError("Podaj katalog z JSON-ami albo plik ZIP.")
