from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
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


def _job_payload(request_id: int, source: str, source_url: str, relative_path: str, youtube_query: str | None = None) -> dict:
    payload = {
        "request_id": request_id,
        "source": source,
        "source_url": source_url,
        "relative_path": relative_path,
        "favorite": True,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }
    if youtube_query:
        payload["youtube_query"] = youtube_query
    return payload


def queue_remote_synology_job(
    request_id: int,
    source: str,
    source_url: str,
    relative_path: str,
    queue_dir: Path,
    youtube_query: str | None = None,
) -> dict:
    queue_dir.mkdir(parents=True, exist_ok=True)
    payload = _job_payload(request_id, source, source_url, relative_path, youtube_query)
    queue_file = queue_dir / f"job_{request_id}_{source.replace('.', '_')}.json"
    queue_file.write_text(json.dumps(payload, indent=2))
    return {"queue_file": str(queue_file)}


def append_manifest_job(
    request_id: int,
    source: str,
    source_url: str,
    relative_path: str,
    manifest_file: Path,
    youtube_query: str | None = None,
) -> dict:
    payload = _job_payload(request_id, source, source_url, relative_path, youtube_query)
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    with manifest_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")
    return {"manifest_file": str(manifest_file)}
