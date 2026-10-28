import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

STATIC_DIR = Path(__file__).parent / "static"

load_dotenv()

from app.db import Base, SessionLocal, engine
from app.ingest import (
    SOURCE_FIRE_STATISTICS,
    SOURCE_NAVER_NEWS,
    SOURCE_WIKIPEDIA_ONTHISDAY,
    ingest_raw_materials,
)
from app.models import GeneratedQuestion
from app.process import process_pending_raw_materials
from app.sources.fire_statistics import compute_insights, fetch_all_fire_records
from app.sources.naver_news import fetch_and_parse as fetch_naver_news
from app.sources.wikipedia_onthisday import fetch_onthisday_raw, parse_events

app = FastAPI(title="curiosity-feed")

Base.metadata.create_all(bind=engine)

if os.environ.get("ENABLE_SCHEDULER", "false").lower() == "true":
    from app.scheduler import start_scheduler

    start_scheduler()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/ingest/wikipedia-onthisday")
def ingest_wikipedia_onthisday(db: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    raw = fetch_onthisday_raw(today.month, today.day)
    events = parse_events(raw)
    ingested = ingest_raw_materials(db, SOURCE_WIKIPEDIA_ONTHISDAY, events)
    return {"fetched": len(events), "ingested": ingested}


@app.post("/ingest/fire-statistics")
def ingest_fire_statistics(db: Session = Depends(get_db)):
    records = fetch_all_fire_records()
    insights = compute_insights(records)
    ingested = ingest_raw_materials(db, SOURCE_FIRE_STATISTICS, insights)
    return {"fetched_records": len(records), "insights": len(insights), "ingested": ingested}


@app.post("/ingest/naver-news")
def ingest_naver_news(db: Session = Depends(get_db)):
    items = fetch_naver_news()
    ingested = ingest_raw_materials(db, SOURCE_NAVER_NEWS, items)
    return {"fetched": len(items), "ingested": ingested}


@app.post("/process/gate2")
def process_gate2(limit: int = 10, db: Session = Depends(get_db)):
    created = process_pending_raw_materials(db, limit=limit)
    return {"processed": len(created)}


@app.get("/feed")
def feed(limit: int = 20, db: Session = Depends(get_db)):
    rows = (
        db.query(GeneratedQuestion)
        .order_by(GeneratedQuestion.score.desc())
        .limit(limit)
        .all()
    )
    return [
        {"question": r.question, "answer": r.answer, "score": r.score, "reason": r.reason} for r in rows
    ]
