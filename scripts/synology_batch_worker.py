#!/usr/bin/env python3
from __future__ import annotations

import json
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


def download_url_to_path(url: str, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with out.open("wb") as f:
            shutil.copyfileobj(resp.raw, f)
    mark_favorite(out)
    return out


def download_youtube_query(query: str, out: Path) -> Path:
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
    subprocess.run(cmd, check=True)
    final = out.with_suffix(".mp3")
    if not final.exists():
        raise RuntimeError("yt-dlp did not produce an MP3")
    mark_favorite(final)
    return final


def process_manifest(manifest_file: Path, done_file: Path, nas_root: Path) -> None:
    if not manifest_file.exists():
        print(f"No manifest file found: {manifest_file}")
        return

    done_ids: set[int] = set()
    if done_file.exists():
        for line in done_file.read_text().splitlines():
            if line.strip().isdigit():
                done_ids.add(int(line.strip()))

    processed: list[int] = []
    for line in manifest_file.read_text().splitlines():
        if not line.strip():
            continue
        job = json.loads(line)
        request_id = int(job["request_id"])
        if request_id in done_ids:
            continue

        rel = job["relative_path"]
        out = nas_root / rel
        source = job.get("source", "")

        if source == "youtube":
            query = job.get("youtube_query")
            if not query:
                continue
            download_youtube_query(query, out.with_suffix(".mp3"))
        else:
            download_url_to_path(job["source_url"], out)

        processed.append(request_id)

    if processed:
        with done_file.open("a", encoding="utf-8") as f:
            for rid in processed:
                f.write(f"{rid}\n")
        print(f"Processed {len(processed)} jobs")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process SaveThatTune Synology manifest jobs")
    parser.add_argument("--manifest", required=True, help="Path to NDJSON manifest file")
    parser.add_argument("--done", required=True, help="Path to file tracking processed request IDs")
    parser.add_argument("--nas-root", required=True, help="NAS music root path")
    args = parser.parse_args()

    process_manifest(Path(args.manifest), Path(args.done), Path(args.nas_root))
