import logging
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.db import SessionLocal
from app.ingest import (
    SOURCE_FIRE_STATISTICS,
    SOURCE_NAVER_NEWS,
    SOURCE_WIKIPEDIA_ONTHISDAY,
    ingest_raw_materials,
)
from app.process import process_pending_raw_materials
from app.sources.fire_statistics import compute_insights, fetch_all_fire_records
from app.sources.naver_news import fetch_and_parse as fetch_naver_news
from app.sources.wikipedia_onthisday import fetch_onthisday_raw, parse_events

log = logging.getLogger(__name__)

GATE2_CHUNK_SIZE = 5
GATE2_MAX_PER_RUN = 60
GATE2_CHUNK_PAUSE_SECONDS = 5.0


def _ingest_wikipedia(session) -> int:
    today = datetime.now(timezone.utc).date()
    events = parse_events(fetch_onthisday_raw(today.month, today.day))
    return ingest_raw_materials(session, SOURCE_WIKIPEDIA_ONTHISDAY, events)


def _ingest_fire_statistics(session) -> int:
    insights = compute_insights(fetch_all_fire_records())
    return ingest_raw_materials(session, SOURCE_FIRE_STATISTICS, insights)


def _ingest_naver_news(session) -> int:
    return ingest_raw_materials(session, SOURCE_NAVER_NEWS, fetch_naver_news())


DEFAULT_INGEST_JOBS = [
    ("wikipedia_onthisday", _ingest_wikipedia),
    ("data_go_kr_fire_statistics", _ingest_fire_statistics),
    ("naver_news", _ingest_naver_news),
]


def run_ingestion(session, ingest_jobs=DEFAULT_INGEST_JOBS) -> dict:
    """소스별로 수집한다. 하나가 실패해도(네트워크, 키 만료 등) 나머지는 계속 진행한다."""
    results = {}
    for name, ingest_fn in ingest_jobs:
        try:
            results[name] = ingest_fn(session)
        except Exception:
            log.exception("%s 수집 실패", name)
            results[name] = None
    return results


def run_gate2_until_caught_up(
    session,
    chunk_size: int = GATE2_CHUNK_SIZE,
    max_total: int = GATE2_MAX_PER_RUN,
    pause_seconds: float = GATE2_CHUNK_PAUSE_SECONDS,
    sleep=time.sleep,
    process_fn=process_pending_raw_materials,
) -> int:
    """Gate2를 작은 묶음으로 나눠서 처리한다 (Groq 무료 티어 TPM 한도 때문에 한꺼번에 몰아치면 안 됨).

    묶음에서 하나도 못 만들면(남은 게 없거나 전부 실패) 멈춘다. 영구적으로
    실패하는 원재료가 있으면 다음 날 다시 시도되는데, 이건 알려진 한계로
    남겨둔다(재시도 횟수 추적 같은 건 지금 단계에서는 오버엔지니어링).
    """
    total_processed = 0
    while total_processed < max_total:
        created = process_fn(session, limit=chunk_size)
        total_processed += len(created)
        if not created:
            break
        sleep(pause_seconds)
    return total_processed


def run_daily_pipeline() -> None:
    session = SessionLocal()
    try:
        log.info("일일 수집 시작")
        log.info("수집 결과: %s", run_ingestion(session))
        processed = run_gate2_until_caught_up(session)
        log.info("Gate2 처리 완료: %d건", processed)
    finally:
        session.close()


def start_scheduler() -> BackgroundScheduler:
    """매일 한 번(UTC 18:00 = KST 새벽 3시) 전체 파이프라인을 돌리는 백그라운드 스케줄러를 시작한다."""
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(run_daily_pipeline, "cron", hour=18, minute=0, id="daily_pipeline")
    scheduler.start()
    log.info("스케줄러 시작됨 (매일 UTC 18:00 실행)")
    return scheduler
