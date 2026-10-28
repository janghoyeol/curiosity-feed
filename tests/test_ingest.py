from app.ingest import ingest_raw_materials
from app.models import RawMaterial


def test_ingest_raw_materials_saves_new_items(session):
    items = [
        {"external_id": "a1", "text": "충분히 긴 원재료 텍스트 1"},
        {"external_id": "a2", "text": "충분히 긴 원재료 텍스트 2"},
    ]

    count = ingest_raw_materials(session, "wikipedia_onthisday", items)

    assert count == 2
    assert session.query(RawMaterial).count() == 2


def test_ingest_raw_materials_skips_duplicates_and_too_short(session):
    session.add(RawMaterial(source="wikipedia_onthisday", external_id="dup", text="이미 있는 원재료"))
    session.commit()

    items = [
        {"external_id": "dup", "text": "이미 있는 원재료"},  # 중복
        {"external_id": "short", "text": "짧음"},  # 너무 짧음
        {"external_id": "new", "text": "새로 들어오는 충분히 긴 원재료"},
    ]

    count = ingest_raw_materials(session, "wikipedia_onthisday", items)

    assert count == 1
    assert session.query(RawMaterial).filter_by(external_id="new").count() == 1


def test_ingest_raw_materials_dedupes_within_same_batch(session):
    # 네이버뉴스처럼 여러 검색어로 수집하면 같은 기사가 한 배치 안에서 두 번 걸릴 수 있다
    items = [
        {"external_id": "same-link", "text": "같은 기사가 두 검색어에 다 걸림"},
        {"external_id": "same-link", "text": "같은 기사가 두 검색어에 다 걸림"},
    ]

    count = ingest_raw_materials(session, "naver_news", items)

    assert count == 1
    assert session.query(RawMaterial).filter_by(external_id="same-link").count() == 1
