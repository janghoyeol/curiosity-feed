from typing import Callable

from sqlalchemy.orm import Session

from app.gate2 import run_gate2
from app.llm.groq_client import chat_completion
from app.models import GeneratedQuestion, RawMaterial


def process_pending_raw_materials(
    session: Session,
    limit: int = 10,
    llm_call: Callable[..., str] = chat_completion,
) -> list[GeneratedQuestion]:
    """아직 Gate2를 거치지 않은 RawMaterial을 가져와 질문 생성+평가하고 저장한다."""
    pending = (
        session.query(RawMaterial)
        .filter(~RawMaterial.generated_questions.any())
        .limit(limit)
        .all()
    )

    created = []
    for material in pending:
        scored = run_gate2(material.text, llm_call=llm_call)
        generated = GeneratedQuestion(
            raw_material_id=material.id,
            question=scored.question,
            score=scored.score,
            reason=scored.reason,
        )
        session.add(generated)
        created.append(generated)

    session.commit()
    return created
