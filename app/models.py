from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func

from app.db import Base


class RawMaterial(Base):
    __tablename__ = "raw_materials"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_source_external_id"),)

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    text = Column(String, nullable=False)
    fetched_at = Column(DateTime, server_default=func.now(), nullable=False)
