import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.gate1 import is_too_short, passes_gate1
from app.models import RawMaterial


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


def test_is_too_short_true_for_short_text():
    assert is_too_short("짧음") is True


def test_is_too_short_false_for_normal_text():
    assert is_too_short("문어는 심장이 3개나 있다고 한다") is False


def test_passes_gate1_true_for_new_valid_material(session):
    assert passes_gate1(session, "wikipedia", "octopus-heart", "문어는 심장이 3개나 있다") is True


def test_passes_gate1_false_for_too_short_text(session):
    assert passes_gate1(session, "wikipedia", "short-1", "짧음") is False


def test_passes_gate1_false_for_duplicate(session):
    material = RawMaterial(source="wikipedia", external_id="dup-1", text="이미 저장된 원재료 텍스트")
    session.add(material)
    session.commit()

    assert passes_gate1(session, "wikipedia", "dup-1", "이미 저장된 원재료 텍스트") is False
