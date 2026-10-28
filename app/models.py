from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.db import Base


class RawMaterial(Base):
    __tablename__ = "raw_materials"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_source_external_id"),)

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    text = Column(String, nullable=False)
    fetched_at = Column(DateTime, server_default=func.now(), nullable=False)

    generated_questions = relationship("GeneratedQuestion", back_populates="raw_material")


class GeneratedQuestion(Base):
    __tablename__ = "generated_questions"

    id = Column(Integer, primary_key=True)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    raw_material = relationship("RawMaterial", back_populates="generated_questions")
