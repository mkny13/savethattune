from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests
from dateutil import parser as date_parser

from app.services.matching import score_track_match


@dataclass
class Candidate:
    source: str
    artist: str
    title: str
    score: float
    raw: dict[str, Any]


def parse_date_fuzzy(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except Exception:
        return None


class SpotifyClient:
    def __init__(self, client_id: str | None, client_secret: str | None, refresh_token: str | None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

    def _token(self) -> str | None:
        if not (self.client_id and self.client_secret and self.refresh_token):
            return None
        creds = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
            headers={"Authorization": f"Basic {creds}"},
            timeout=20,
        )
        if not resp.ok:
            return None
        return resp.json().get("access_token")

    def search(self, artist: str, title: str) -> list[Candidate]:
        token = self._token()
        if not token:
            return []
        q = f"track:{title} artist:{artist}"
        resp = requests.get(
            "https://api.spotify.com/v1/search",
            params={"q": q, "type": "track", "limit": 10},
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        if not resp.ok:
            return []
        items = resp.json().get("tracks", {}).get("items", [])
        out: list[Candidate] = []
        for item in items:
            cand_artist = item["artists"][0]["name"]
            cand_title = item["name"]
            out.append(
                Candidate(
                    source="spotify",
                    artist=cand_artist,
                    title=cand_title,
                    score=score_track_match(artist, title, cand_artist, cand_title),
                    raw=item,
                )
            )
        return sorted(out, key=lambda c: c.score, reverse=True)

    def save_to_library(self, track_id: str) -> bool:
        token = self._token()
        if not token:
            return False
        resp = requests.put(
            "https://api.spotify.com/v1/me/tracks",
            params={"ids": track_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        return resp.status_code in {200, 201, 204}


class LMAClient:
    def search(self, artist: str, title: str) -> list[Candidate]:
        query = f'title:("{title}") AND creator:("{artist}") AND mediatype:(audio)'
        resp = requests.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": query,
                "fl[]": ["identifier", "title", "creator", "date"],
                "rows": 20,
                "page": 1,
                "output": "json",
            },
            timeout=30,
        )
        if not resp.ok:
            return []
        docs = resp.json().get("response", {}).get("docs", [])
        return sorted(
            [
                Candidate(
                    source="lma",
                    artist=d.get("creator", ""),
                    title=d.get("title", ""),
                    score=score_track_match(artist, title, d.get("creator", ""), d.get("title", "")),
                    raw=d,
                )
                for d in docs
            ],
            key=lambda c: c.score,
            reverse=True,
        )


class PhishInClient:
    def __init__(self, api_key: str | None):
        self.api_key = api_key

    def search(self, artist: str, title: str) -> list[Candidate]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = requests.get("https://phish.in/api/v1/songs", params={"title": title, "per_page": 25}, headers=headers, timeout=20)
        if not resp.ok:
            return []
        data = resp.json().get("data", [])
        return sorted(
            [
                Candidate(
                    source="phish.in",
                    artist=artist,
                    title=item.get("title", ""),
                    score=score_track_match(artist, title, artist, item.get("title", "")),
                    raw=item,
                )
                for item in data
            ],
            key=lambda c: c.score,
            reverse=True,
        )
