"""Escalation checks and answer post-processing, with the Claude API replaced by fakes."""

from types import SimpleNamespace

import pytest

import src.answer as answer_module
import src.escalation as escalation_module
from src.escalation import check_answer, check_question, check_retrieval
from src.models import Answer, Citation, DocName, EscalationCategory
from tests.conftest import make_retrieved


class FakeClient:
    """Stands in for anthropic.Anthropic: returns a fixed parsed_output and records calls."""

    def __init__(self, parsed_output, stop_reason="end_turn"):
        self.calls = 0
        response = SimpleNamespace(parsed_output=parsed_output, stop_reason=stop_reason)

        def parse(**kwargs):
            self.calls += 1
            return response

        self.messages = SimpleNamespace(parse=parse)
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=parse))


def use_fake_client(monkeypatch, module, parsed_output, stop_reason="end_turn") -> FakeClient:
    fake = FakeClient(parsed_output, stop_reason)
    monkeypatch.setattr(module, "get_client", lambda: fake)
    return fake


@pytest.mark.parametrize("question", [
    "I have chest pain and feel dizzy",
    "My friend overdosed",
    "I feel suicidal",
])
def test_emergencies_are_caught_by_rules_without_calling_the_llm(monkeypatch, question):
    fake = use_fake_client(monkeypatch, escalation_module, None)
    decision = check_question(question)
    assert decision.escalate and decision.category == EscalationCategory.EMERGENCY
    assert fake.calls == 0


def test_classifier_result_becomes_an_escalation(monkeypatch):
    output = escalation_module.Classification(category=EscalationCategory.ACCOUNT_SPECIFIC, reason="claim status")
    use_fake_client(monkeypatch, escalation_module, output)
    decision = check_question("Why was my claim rejected?")
    assert decision.escalate and decision.category == EscalationCategory.ACCOUNT_SPECIFIC


def test_classifier_cannot_pick_categories_reserved_for_code(monkeypatch):
    output = escalation_module.Classification(category=EscalationCategory.LOW_CONFIDENCE, reason="x")
    use_fake_client(monkeypatch, escalation_module, output)
    assert not check_question("What is the waiting period?").escalate


def test_weak_retrieval_escalates_and_strong_retrieval_passes():
    assert check_retrieval([make_retrieved(semantic=0.1), make_retrieved(2, semantic=0.2)]).escalate
    assert not check_retrieval([make_retrieved(semantic=0.6)]).escalate
    assert check_retrieval([]).escalate


def test_low_confidence_or_uncited_answer_escalates():
    cited = [Citation(doc=DocName.MEMBER_GUIDE, page=21, section="Having a baby?")]
    assert check_answer(Answer(text="t", confidence=0.2, citations=cited)).escalate
    assert check_answer(Answer(text="t", confidence=0.9)).escalate
    assert not check_answer(Answer(text="t", confidence=0.9, citations=cited)).escalate


def test_format_sources_numbers_each_extract():
    text = answer_module.format_sources([make_retrieved(1), make_retrieved(2)])
    assert text.startswith("[1] (member_guide, page 1,")
    assert "\n\n[2] (member_guide, page 2," in text


def test_citations_come_from_chunks_and_invalid_ids_are_ignored(monkeypatch):
    chunks = [make_retrieved(1), make_retrieved(2, doc=DocName.FUND_RULES, section="F3.7 Waiting Periods")]
    output = answer_module.LLMAnswer(answer="12 months.", source_ids=[2, 2, 9], found_in_sources=True, confidence=1.4)
    use_fake_client(monkeypatch, answer_module, output)

    answer = answer_module.generate_answer("q", chunks)

    assert answer.citations == [Citation(doc=DocName.FUND_RULES, page=2, section="F3.7 Waiting Periods")]
    assert answer.confidence == 1.0   # clamped


def test_not_found_in_sources_gives_zero_confidence_and_no_citations(monkeypatch):
    output = answer_module.LLMAnswer(answer="Not in the documents.", source_ids=[1], found_in_sources=False, confidence=0.8)
    use_fake_client(monkeypatch, answer_module, output)
    answer = answer_module.generate_answer("q", [make_retrieved(1)])
    assert answer.confidence == 0.0 and answer.citations == []


def test_refusal_returns_a_safe_message(monkeypatch):
    use_fake_client(monkeypatch, answer_module, None, stop_reason="refusal")
    answer = answer_module.generate_answer("q", [make_retrieved(1)])
    assert answer.confidence == 0.0 and "132 331" in answer.text
