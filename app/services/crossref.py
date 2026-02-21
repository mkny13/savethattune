from __future__ import annotations

import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DEADDISC_URL = "https://www.deaddisc.com/GDFD_Dead_By_Date.htm"
PHISHNET_URL = "https://phish.net/charts/livephish"


def _cache_load(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _cache_save(path: Path, mapping: dict[str, str]) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping, indent=2))
    return mapping


def load_deaddisc_or_refresh(path: Path, force_refresh: bool = False) -> dict[str, str]:
    cached = _cache_load(path)
    if cached is not None and not force_refresh:
        return cached

    html = requests.get(DEADDISC_URL, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")
    mapping: dict[str, str] = {}

    for row in soup.select("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        if len(cells) < 3:
            continue
        date = cells[0]
        title = cells[1]
        if re.match(r"\d{1,2}/\d{1,2}/\d{2,4}", date):
            mapping[title.lower()] = date

    return _cache_save(path, mapping)


def load_phishnet_or_refresh(path: Path, force_refresh: bool = False) -> dict[str, str]:
    cached = _cache_load(path)
    if cached is not None and not force_refresh:
        return cached

    html = requests.get(PHISHNET_URL, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")
    mapping: dict[str, str] = {}

    # Page contents can change. We heuristically map release/show labels to show dates.
    date_regex = re.compile(r"\b(19|20)\d{2}[-/]\d{2}[-/]\d{2}\b")
    for row in soup.select("tr"):
        row_text = row.get_text(" ", strip=True)
        date_match = date_regex.search(row_text)
        if not date_match:
            continue
        date_value = date_match.group(0).replace("/", "-")
        cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        label = ""
        for cell in cells:
            if cell and not date_regex.search(cell):
                label = cell
                break
        if label:
            mapping[label.lower()] = date_value

    return _cache_save(path, mapping)


def load_crossref_for_artist(artist: str, deaddisc_path: Path, phishnet_path: Path) -> dict[str, str]:
    normalized = artist.strip().lower()
    if normalized in {"phish", "phïsh"}:
        return load_phishnet_or_refresh(phishnet_path)
    return load_deaddisc_or_refresh(deaddisc_path)
