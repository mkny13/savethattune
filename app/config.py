from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    api_key: str
    sqlite_path: Path
    nas_music_root: Path
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    mail_from: str | None
    mail_to: str | None
    spotify_client_id: str | None
    spotify_client_secret: str | None
    spotify_refresh_token: str | None
    phish_in_api_key: str | None
    deaddisc_cache_path: Path
    phishnet_cache_path: Path


def load_settings() -> Settings:
    return Settings(
        api_key=os.getenv("SAVE_THAT_TUNE_API_KEY", "change-me"),
        sqlite_path=Path(os.getenv("SAVE_THAT_TUNE_DB", "data/actions.db")),
        nas_music_root=Path(os.getenv("SAVE_THAT_TUNE_NAS_ROOT", "data/nas_music")),
        smtp_host=os.getenv("SAVE_THAT_TUNE_SMTP_HOST"),
        smtp_port=int(os.getenv("SAVE_THAT_TUNE_SMTP_PORT", "587")),
        smtp_username=os.getenv("SAVE_THAT_TUNE_SMTP_USERNAME"),
        smtp_password=os.getenv("SAVE_THAT_TUNE_SMTP_PASSWORD"),
        mail_from=os.getenv("SAVE_THAT_TUNE_MAIL_FROM"),
        mail_to=os.getenv("SAVE_THAT_TUNE_MAIL_TO"),
        spotify_client_id=os.getenv("SAVE_THAT_TUNE_SPOTIFY_CLIENT_ID"),
        spotify_client_secret=os.getenv("SAVE_THAT_TUNE_SPOTIFY_CLIENT_SECRET"),
        spotify_refresh_token=os.getenv("SAVE_THAT_TUNE_SPOTIFY_REFRESH_TOKEN"),
        phish_in_api_key=os.getenv("SAVE_THAT_TUNE_PHISHIN_API_KEY"),
        deaddisc_cache_path=Path(os.getenv("SAVE_THAT_TUNE_DEADDISC_CACHE", "data/deaddisc_cache.json")),
        phishnet_cache_path=Path(os.getenv("SAVE_THAT_TUNE_PHISHNET_CACHE", "data/phishnet_cache.json")),
    )
