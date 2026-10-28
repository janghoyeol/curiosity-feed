from sqlalchemy.orm import Session

from app.gate1 import passes_gate1
from app.models import RawMaterial

SOURCE_WIKIPEDIA_ONTHISDAY = "wikipedia_onthisday"
SOURCE_FIRE_STATISTICS = "data_go_kr_fire_statistics"


def ingest_raw_materials(session: Session, source: str, items: list[dict]) -> int:
    """Gate1을 통과한 원재료만 RawMaterial로 저장하고, 저장된 개수를 반환한다."""
    ingested = 0
    for item in items:
        if not passes_gate1(session, source, item["external_id"], item["text"]):
            continue
        session.add(RawMaterial(source=source, external_id=item["external_id"], text=item["text"]))
        ingested += 1
    session.commit()
    return ingested
