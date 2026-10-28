from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.ingest import SOURCE_WIKIPEDIA_ONTHISDAY, ingest_raw_materials
from app.sources.wikipedia_onthisday import fetch_onthisday_raw, parse_events

app = FastAPI(title="curiosity-feed")

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest/wikipedia-onthisday")
def ingest_wikipedia_onthisday(db: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    raw = fetch_onthisday_raw(today.month, today.day)
    events = parse_events(raw)
    ingested = ingest_raw_materials(db, SOURCE_WIKIPEDIA_ONTHISDAY, events)
    return {"fetched": len(events), "ingested": ingested}
