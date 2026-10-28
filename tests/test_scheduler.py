from app.scheduler import run_gate2_until_caught_up, run_ingestion, start_scheduler


def test_run_ingestion_continues_after_one_source_fails(session):
    calls = []

    def ok_source(s):
        calls.append("ok")
        return 3

    def failing_source(s):
        calls.append("fail")
        raise RuntimeError("API 키 만료 등")

    results = run_ingestion(session, ingest_jobs=[("ok_source", ok_source), ("bad_source", failing_source)])

    assert calls == ["ok", "fail"]
    assert results == {"ok_source": 3, "bad_source": None}


def test_run_gate2_until_caught_up_stops_when_nothing_pending(session):
    sleeps = []

    processed = run_gate2_until_caught_up(session, chunk_size=5, max_total=60, sleep=sleeps.append)

    assert processed == 0
    assert sleeps == []  # 처리할 게 없으면 애초에 쉴 필요도 없음


def test_run_gate2_until_caught_up_processes_in_chunks_with_pause():
    # process_fn을 가짜로 주입해서, 실제 LLM/DB 없이 청크 나누기+대기 로직만 검증한다
    chunk_sizes_requested = []
    remaining = [3, 3, 1, 0]  # 세 번은 뭔가 처리되고, 네 번째에 0개 → 멈춰야 함

    def fake_process_fn(session, limit):
        chunk_sizes_requested.append(limit)
        count = remaining.pop(0)
        return ["item"] * count

    sleeps = []

    processed = run_gate2_until_caught_up(
        session=None,
        chunk_size=3,
        max_total=60,
        sleep=sleeps.append,
        pause_seconds=1.5,
        process_fn=fake_process_fn,
    )

    assert processed == 7  # 3 + 3 + 1
    assert chunk_sizes_requested == [3, 3, 3, 3]  # 0개 받은 네 번째 호출까지 포함
    assert sleeps == [1.5, 1.5, 1.5]  # 0개를 받은 마지막엔 쉬지 않음


def test_run_gate2_until_caught_up_respects_max_total():
    def fake_process_fn(session, limit):
        return ["item"] * limit  # 끝없이 더 있다고 가정

    processed = run_gate2_until_caught_up(
        session=None, chunk_size=5, max_total=12, sleep=lambda s: None, process_fn=fake_process_fn
    )

    assert processed == 15  # 5+5+5, max_total(12)를 넘긴 다음 루프에서 멈춤


def test_start_scheduler_registers_daily_job():
    scheduler = start_scheduler()
    try:
        job = scheduler.get_job("daily_pipeline")
        assert job is not None
    finally:
        scheduler.shutdown(wait=False)
