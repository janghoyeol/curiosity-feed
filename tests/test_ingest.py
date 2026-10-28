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
