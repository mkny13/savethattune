from app.services.pipeline import _search_order


def test_phish_routes_to_phishin_not_lma():
    assert _search_order("Phish") == ["spotify", "phish.in"]


def test_non_phish_routes_to_lma():
    assert _search_order("Grateful Dead") == ["spotify", "lma"]
