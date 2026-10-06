import pytest
from pydantic import ValidationError

from src.models import Answer, ChatResponse, Chunk, EscalationCategory, EscalationDecision


def test_valid_chunk_round_trips_through_json():
    chunk = Chunk(chunk_id="x", doc="fund_rules", page=1, section="A1", text="hi")
    assert Chunk.model_validate_json(chunk.model_dump_json()) == chunk


@pytest.mark.parametrize("field, value", [("page", 0), ("doc", "random_doc")])
def test_chunk_rejects_bad_values(field, value):
    data = {"chunk_id": "x", "doc": "fund_rules", "page": 1, "section": "A1", "text": "hi", field: value}
    with pytest.raises(ValidationError):
        Chunk(**data)


@pytest.mark.parametrize("confidence", [-0.1, 1.5])
def test_answer_confidence_must_be_between_0_and_1(confidence):
    with pytest.raises(ValidationError):
        Answer(text="t", confidence=confidence)


def test_escalated_response_cannot_include_an_answer():
    with pytest.raises(ValidationError):
        ChatResponse(
            message="m",
            answer=Answer(text="t", confidence=0.9),
            escalation=EscalationDecision(escalate=True, category=EscalationCategory.COMPLAINT),
        )


def test_answered_response_must_include_an_answer():
    with pytest.raises(ValidationError):
        ChatResponse(message="m", escalation=EscalationDecision(escalate=False))
