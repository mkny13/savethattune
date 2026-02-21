from app.services.matching import normalize_text, score_track_match


def test_normalize_text_removes_feat_and_punctuation():
    assert normalize_text("Eyes of the World (feat. Guest)!") == "eyes of the world"


def test_score_track_match_prefers_similar_titles():
    high = score_track_match("Grateful Dead", "Estimated Prophet", "Grateful Dead", "Estimated Prophet - Live")
    low = score_track_match("Grateful Dead", "Estimated Prophet", "Phish", "Reba")
    assert high > low
    assert high > 70
