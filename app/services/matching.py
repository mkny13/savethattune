from __future__ import annotations

import re
from rapidfuzz import fuzz


def normalize_text(value: str) -> str:
    text = value.lower().strip()
    text = re.sub(r"\(.*?\)|\[.*?\]", "", text)
    text = re.sub(r"\bfeat\.?\b.*$", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def score_track_match(input_artist: str, input_title: str, candidate_artist: str, candidate_title: str) -> float:
    artist_score = fuzz.token_set_ratio(normalize_text(input_artist), normalize_text(candidate_artist))
    title_score = fuzz.token_set_ratio(normalize_text(input_title), normalize_text(candidate_title))
    return (artist_score * 0.35) + (title_score * 0.65)
