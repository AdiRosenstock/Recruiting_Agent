from app.services.outreach.banned_phrases import find_banned_phrases


def test_detects_banned_phrase_case_insensitive() -> None:
    text = "I would bring Significant Ownership to this role."
    assert find_banned_phrases(text) == ["significant ownership"]


def test_detects_multiple_banned_phrases() -> None:
    text = "This is a revolutionary product and I love the synergy here."
    hits = find_banned_phrases(text)
    assert "revolutionary" in hits
    assert "synergy" in hits


def test_clean_text_has_no_hits() -> None:
    text = "Hi, I really liked what you're building with the data pipeline. Let's chat."
    assert find_banned_phrases(text) == []


def test_thrilled_to_apply_is_flagged() -> None:
    assert find_banned_phrases("I am thrilled to apply for this position.") == [
        "i am thrilled to apply"
    ]
