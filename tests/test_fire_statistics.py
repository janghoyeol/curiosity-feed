from app.sources.fire_statistics import compute_insights


def _record(**overrides):
    base = {
        "일시": "2024-06-01 03:00:00",
        "시도": "서울특별시",
        "시_군_구": "강남구",
        "화재유형": "건축,구조물",
        "발화요인대분류": "부주의",
        "재산피해소계": 100,
    }
    base.update(overrides)
    return base


def test_compute_insights_returns_empty_for_no_records():
    assert compute_insights([]) == []


def test_compute_insights_picks_most_common_cause():
    records = [_record(발화요인대분류="부주의")] * 3 + [_record(발화요인대분류="전기적 요인")]

    insights = compute_insights(records)
    top_cause = next(i for i in insights if i["external_id"] == "fire:2024:top_cause")

    assert "부주의" in top_cause["text"]
    assert "75.0%" in top_cause["text"]


def test_compute_insights_picks_most_common_region():
    records = [_record(시도="서울특별시")] * 2 + [_record(시도="부산광역시")]

    insights = compute_insights(records)
    top_region = next(i for i in insights if i["external_id"] == "fire:2024:top_region")

    assert "서울특별시" in top_region["text"]
    assert "2건" in top_region["text"]


def test_compute_insights_sums_damage_by_fire_type():
    records = [
        _record(화재유형="건축,구조물", 재산피해소계=1000),
        _record(화재유형="자동차,철도차량", 재산피해소계=50),
        _record(화재유형="건축,구조물", 재산피해소계=2000),
    ]

    insights = compute_insights(records)
    worst_type = next(i for i in insights if i["external_id"] == "fire:2024:worst_damage_type")

    assert "건축,구조물" in worst_type["text"]
    assert "3,000원" in worst_type["text"]


def test_compute_insights_finds_peak_hour():
    records = [_record(일시="2024-01-01 03:00:00")] * 3 + [_record(일시="2024-01-01 09:00:00")]

    insights = compute_insights(records)
    peak_hour = next(i for i in insights if i["external_id"] == "fire:2024:peak_hour")

    assert "3시" in peak_hour["text"]


def test_compute_insights_finds_worst_single_fire():
    records = [
        _record(시도="서울특별시", 시_군_구="강남구", 재산피해소계=100),
        _record(시도="부산광역시", 시_군_구="해운대구", 재산피해소계=999999),
    ]

    insights = compute_insights(records)
    worst_single = next(i for i in insights if i["external_id"] == "fire:2024:worst_single_fire")

    assert "부산광역시" in worst_single["text"]
    assert "999,999원" in worst_single["text"]


def test_compute_insights_external_ids_are_stable_across_reruns():
    records = [_record()] * 5

    first = compute_insights(records)
    second = compute_insights(records)

    assert [i["external_id"] for i in first] == [i["external_id"] for i in second]
