import logging
from typing import Callable

from sqlalchemy.orm import Session

from app.gate2 import run_gate2
from app.llm.groq_client import chat_completion
from app.models import GeneratedQuestion, RawMaterial

log = logging.getLogger(__name__)


def process_pending_raw_materials(
    session: Session,
    limit: int = 10,
    llm_call: Callable[..., str] = chat_completion,
) -> list[GeneratedQuestion]:
    """아직 Gate2를 거치지 않은 RawMaterial을 가져와 질문 생성+평가하고 저장한다.

    항목마다 바로 커밋한다. 스케줄러로 매일 자동 돌리면 LLM 호출 하나가
    실패하는 일이 결국 생기는데, 그때 이미 성공한 항목들까지 통째로
    날아가면 안 되기 때문이다. 실패한 항목은 로그만 남기고 다음 항목으로
    넘어간다.
    """
    pending = (
        session.query(RawMaterial)
        .filter(~RawMaterial.generated_questions.any())
        .limit(limit)
        .all()
    )

    created = []
    for material in pending:
        try:
            scored = run_gate2(material.text, llm_call=llm_call)
        except Exception:
            log.exception("Gate2 처리 실패 (raw_material_id=%s), 다음 항목으로 넘어감", material.id)
            continue

        generated = GeneratedQuestion(
            raw_material_id=material.id,
            question=scored.question,
            score=scored.score,
            reason=scored.reason,
        )
        session.add(generated)
        session.commit()
        created.append(generated)

    return created
