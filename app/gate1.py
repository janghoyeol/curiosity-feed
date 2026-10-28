from sqlalchemy.orm import Session

from app.models import RawMaterial

MIN_TEXT_LENGTH = 10


def is_too_short(text: str) -> bool:
    return len(text.strip()) < MIN_TEXT_LENGTH


def is_duplicate(session: Session, source: str, external_id: str) -> bool:
    existing = (
        session.query(RawMaterial)
        .filter_by(source=source, external_id=external_id)
        .first()
    )
    return existing is not None


def passes_gate1(session: Session, source: str, external_id: str, text: str) -> bool:
    if is_too_short(text):
        return False
    if is_duplicate(session, source, external_id):
        return False
    return True
