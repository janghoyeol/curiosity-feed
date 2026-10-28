from app.models import GeneratedQuestion, RawMaterial
from app.process import process_pending_raw_materials


def test_process_pending_raw_materials_skips_already_processed(session):
    already_done = RawMaterial(source="wikipedia_onthisday", external_id="done-1", text="이미 처리된 원재료")
    pending = RawMaterial(source="wikipedia_onthisday", external_id="pending-1", text="아직 처리 안 된 원재료")
    session.add_all([already_done, pending])
    session.commit()

    session.add(
        GeneratedQuestion(
            raw_material_id=already_done.id, question="기존 질문", answer="기존 답", score=3.0, reason="기존"
        )
    )
    session.commit()

    responses = iter(['{"question": "새로 생성된 질문", "answer": "새로 생성된 답"}', '{"score": 4.0, "reason": "사실형"}'])

    def fake_llm_call(prompt, **kwargs):
        return next(responses)

    created = process_pending_raw_materials(session, limit=10, llm_call=fake_llm_call)

    assert len(created) == 1
    assert created[0].raw_material_id == pending.id
    assert created[0].question == "새로 생성된 질문"
    assert created[0].answer == "새로 생성된 답"
    assert created[0].score == 4.0
    assert session.query(GeneratedQuestion).count() == 2


def test_process_pending_raw_materials_respects_limit(session):
    for i in range(3):
        session.add(RawMaterial(source="wikipedia_onthisday", external_id=f"m{i}", text=f"원재료 {i}"))
    session.commit()

    def fake_llm_call(prompt, **kwargs):
        if "score" in prompt:  # SCORING_PROMPT만 JSON 포맷 지시에 "score"를 포함함
            return '{"score": 3.0, "reason": "이유"}'
        return '{"question": "생성된 질문", "answer": "생성된 답"}'

    created = process_pending_raw_materials(session, limit=2, llm_call=fake_llm_call)

    assert len(created) == 2


def test_process_pending_raw_materials_keeps_earlier_successes_when_later_item_fails(session):
    ok = RawMaterial(source="wikipedia_onthisday", external_id="ok-1", text="성공할 원재료")
    fails = RawMaterial(source="wikipedia_onthisday", external_id="fail-1", text="실패할 원재료")
    session.add_all([ok, fails])
    session.commit()

    call_count = {"n": 0}

    def flaky_llm_call(prompt, **kwargs):
        call_count["n"] += 1
        if call_count["n"] <= 2:
            if "score" in prompt:
                return '{"score": 4.0, "reason": "이유"}'
            return '{"question": "성공 질문", "answer": "성공 답"}'
        raise RuntimeError("레이트리밋 등으로 실패")

    created = process_pending_raw_materials(session, limit=10, llm_call=flaky_llm_call)

    # 첫 번째 원재료는 성공해서 커밋됐어야 하고, 두 번째가 실패해도 예외가 올라오지 않아야 한다
    assert len(created) == 1
    assert session.query(GeneratedQuestion).count() == 1
