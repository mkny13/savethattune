from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import requests
from mutagen.flac import FLAC
from mutagen.id3 import ID3, TXXX


def mark_favorite(path: Path) -> None:
    if path.suffix.lower() == ".mp3":
        tags = ID3(path)
        tags.add(TXXX(encoding=3, desc="Favorite", text="1"))
        tags.save(v2_version=3)
    elif path.suffix.lower() == ".flac":
        tags = FLAC(path)
        tags["FAVORITE"] = "1"
        tags.save()


def download_to_nas(url: str, nas_root: Path, relative_path: str) -> Path:
    out = nas_root / relative_path
    out.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with out.open("wb") as f:
            shutil.copyfileobj(r.raw, f)
    mark_favorite(out)
    return out


def download_from_youtube(query: str, nas_root: Path, relative_path: str) -> Path | None:
    out = nas_root / relative_path
    out.parent.mkdir(parents=True, exist_ok=True)
    output_template = str(out.with_suffix(".%(ext)s"))
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "-o",
        output_template,
        f"ytsearch1:{query}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    final = out.with_suffix(".mp3")
    if not final.exists():
        return None
    mark_favorite(final)
    return final
