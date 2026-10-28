from app.sources.wikipedia_onthisday import parse_events


def test_parse_events_extracts_text_and_stable_external_id():
    raw = {
        "events": [
            {"text": "Some historical event happened.", "year": 1990},
            {"text": "Some historical event happened.", "year": 1990},  # 중복 텍스트
        ]
    }

    parsed = parse_events(raw)

    assert len(parsed) == 2
    assert parsed[0]["text"] == "Some historical event happened."
    # 같은 텍스트면 같은 external_id가 나와야 Gate1의 중복 체크가 의미를 가짐
    assert parsed[0]["external_id"] == parsed[1]["external_id"]


def test_parse_events_skips_empty_text():
    raw = {"events": [{"text": "   ", "year": 2000}, {"text": "Valid event", "year": 2001}]}

    parsed = parse_events(raw)

    assert len(parsed) == 1
    assert parsed[0]["text"] == "Valid event"


def test_parse_events_handles_missing_events_key():
    assert parse_events({}) == []
