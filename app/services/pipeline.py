from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from app.config import Settings
from app.db import Database
from app.services.crossref import load_crossref_for_artist
from app.services.notifier import send_email
from app.services.saver import append_manifest_job, download_from_youtube, download_to_nas, queue_remote_synology_job
from app.services.sources import LMAClient, PhishInClient, SpotifyClient


def _build_download_url(source: str, raw: dict) -> str | None:
    if source == "lma":
        identifier = raw.get("identifier")
        if not identifier:
            return None
        return f"https://archive.org/download/{identifier}/{identifier}_vbr.mp3"
    if source == "phish.in":
        return raw.get("mp3")
    return None


def _date_bonus(show_date: str | None, candidate: dict, crossref: dict[str, str]) -> float:
    if not show_date:
        return 0.0
    album_name = (candidate.get("album") or {}).get("name", "").lower()
    release = (candidate.get("album") or {}).get("release_date", "")
    if show_date in release or show_date in album_name:
        return 10.0
    known = crossref.get(album_name)
    if known and show_date.replace("-", "/") in known:
        return 8.0
    return 0.0


def _is_phish_artist(artist: str) -> bool:
    normalized = artist.strip().lower()
    return normalized in {"phish", "phïsh"}


def _search_order(artist: str) -> list[str]:
    return ["spotify", "phish.in"] if _is_phish_artist(artist) else ["spotify", "lma"]


def _safe_rel_path(artist: str, title: str, show_date: str | None, ext: str) -> str:
    safe_artist = "".join(ch for ch in artist if ch.isalnum() or ch in " -_").strip() or "Unknown Artist"
    safe_title = "".join(ch for ch in title if ch.isalnum() or ch in " -_").strip() or "Unknown Title"
    date_prefix = f"{show_date} - " if show_date else ""
    return f"{safe_artist}/{date_prefix}{safe_title}{ext}"


def _handle_remote_dispatch(settings: Settings, request_id: int, source: str, source_url: str, rel: str, youtube_query: str | None = None) -> str:
    if settings.synology_mode == "queue":
        dispatch = queue_remote_synology_job(
            request_id=request_id,
            source=source,
            source_url=source_url,
            relative_path=rel,
            queue_dir=settings.synology_queue_dir,
            youtube_query=youtube_query,
        )
        return f"Queued Synology job file ({dispatch['queue_file']})."

    if settings.synology_mode == "manifest":
        dispatch = append_manifest_job(
            request_id=request_id,
            source=source,
            source_url=source_url,
            relative_path=rel,
            manifest_file=settings.synology_manifest_file,
            youtube_query=youtube_query,
        )
        return f"Appended Synology manifest job ({dispatch['manifest_file']})."

    raise ValueError(f"Unsupported remote mode: {settings.synology_mode}")


def process_capture(db: Database, settings: Settings, request_id: int, artist: str, title: str, show_date: str | None) -> None:
    db.set_status(request_id, "searching")

    spotify = SpotifyClient(settings.spotify_client_id, settings.spotify_client_secret, settings.spotify_refresh_token)
    lma = LMAClient()
    phish = PhishInClient(settings.phish_in_api_key)
    crossref = load_crossref_for_artist(artist, settings.deaddisc_cache_path, settings.phishnet_cache_path) if show_date else {}

    source_clients = {"spotify": spotify, "lma": lma, "phish.in": phish}
    thresholds = {"spotify": 78, "lma": 74, "phish.in": 74}
    source_chain = _search_order(artist)

    candidates = []
    source_name = ""
    for idx, source in enumerate(source_chain):
        source_name = source
        candidates = source_clients[source].search(artist, title)
        if source == "spotify":
            for c in candidates:
                c.score += _date_bonus(show_date, c.raw, crossref)
            candidates.sort(key=lambda x: x.score, reverse=True)

        top_score = candidates[0].score if candidates else None
        if candidates and top_score >= thresholds[source]:
            break
        if idx < len(source_chain) - 1:
            db.log_action(request_id, "search", "fallback", {"from": source, "top_score": top_score})
            continue
        candidates = []

    if not candidates:
        db.log_action(request_id, "search", "fallback", {"from": source_name or "none", "to": "youtube"})
        db.set_status(request_id, "saving")
        rel = _safe_rel_path(artist, title, show_date, ".mp3")
        yt_query = f"{artist} {title} {show_date or ''} live"

        if settings.synology_mode in {"queue", "manifest"}:
            yt_search_url = f"https://www.youtube.com/results?search_query={yt_query.replace(' ', '+')}"
            save_message = _handle_remote_dispatch(settings, request_id, "youtube", yt_search_url, rel, youtube_query=yt_query)
            db.log_action(request_id, "save", "queued_remote", {"source": "youtube", "message": save_message})
            db.set_status(request_id, "done")
            send_email(settings.smtp_host, settings.smtp_port, settings.smtp_username, settings.smtp_password, settings.mail_from, settings.mail_to, f"SaveThatTune request #{request_id}: youtube queued", f"Request: {artist} - {title} ({show_date or 'no date'})\nResult: {save_message}")
            return

        yt_path = download_from_youtube(yt_query, settings.nas_music_root, rel)
        if yt_path:
            save_message = f"Downloaded YouTube audio to {yt_path}."
            db.log_action(request_id, "save", "done", {"source": "youtube", "message": save_message})
            db.set_status(request_id, "done")
            send_email(settings.smtp_host, settings.smtp_port, settings.smtp_username, settings.smtp_password, settings.mail_from, settings.mail_to, f"SaveThatTune request #{request_id}: youtube", f"Request: {artist} - {title} ({show_date or 'no date'})\nResult: {save_message}")
            return

        db.set_status(request_id, "no_match")
        db.log_action(request_id, "search", "no_match", {"artist": artist, "title": title, "show_date": show_date, "youtube_attempted": True})
        send_email(settings.smtp_host, settings.smtp_port, settings.smtp_username, settings.smtp_password, settings.mail_from, settings.mail_to, f"SaveThatTune request #{request_id}: no match", f"No match found for {artist} - {title} ({show_date or 'no date'}). YouTube fallback also failed.")
        return

    best = candidates[0]
    db.log_action(request_id, "search", "matched", {"source": source_name, "score": best.score, "candidate": asdict(best)})

    db.set_status(request_id, "saving")
    if best.source == "spotify":
        ok = spotify.save_to_library(best.raw["id"])
        save_message = f"Spotify save {'succeeded' if ok else 'failed'} for {best.title}."
    else:
        dl = _build_download_url(best.source, best.raw)
        if dl:
            ext = ".flac" if dl.lower().endswith(".flac") else ".mp3"
            rel = _safe_rel_path(artist, title, show_date, ext)
            if settings.synology_mode in {"queue", "manifest"}:
                save_message = _handle_remote_dispatch(settings, request_id, best.source, dl, rel)
                db.log_action(request_id, "save", "queued_remote", {"source": best.source, "message": save_message, "url": dl})
            else:
                final_path = download_to_nas(dl, settings.nas_music_root, rel)
                save_message = f"Downloaded {best.source} file to {final_path}."
        else:
            save_message = f"Matched {best.source} but no downloadable URL was found."

    db.log_action(request_id, "save", "done", {"message": save_message})
    db.set_status(request_id, "done")

    send_email(
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_username,
        settings.smtp_password,
        settings.mail_from,
        settings.mail_to,
        f"SaveThatTune request #{request_id}: {best.source}",
        f"Request: {artist} - {title} ({show_date or 'no date'})\nMatch source: {best.source}\nScore: {best.score:.1f}\nResult: {save_message}\nTime: {datetime.utcnow().isoformat()}Z",
    )
