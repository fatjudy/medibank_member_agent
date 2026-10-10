"""Decide when a question should go to a human consultant instead of being answered by the bot."""

import re

from pydantic import BaseModel, Field

from src.answer import MODEL, get_client
from src.models import Answer, EscalationCategory, EscalationDecision, RetrievedChunk

MIN_SEMANTIC_SCORE = 0.30   # below this, nothing in the documents really matches the question
MIN_ANSWER_CONFIDENCE = 0.5

# Safety-critical: matched by rules so they never depend on an LLM call.
EMERGENCY_RE = re.compile(
    r"\b(chest pain|can'?t breathe|cannot breathe|heart attack|stroke|overdos\w*|suicid\w*|"
    r"kill myself|self[- ]harm|unconscious|severe bleeding|emergency)\b",
    re.IGNORECASE,
)

MESSAGES = {
    EscalationCategory.EMERGENCY: (
        "If this is a medical emergency, please call 000 now. If you are in crisis, you can call "
        "Lifeline on 13 11 14 at any time."
    ),
    EscalationCategory.ACCOUNT_SPECIFIC: (
        "I can't see your personal membership details, so I'll connect you with a Medibank consultant "
        "who can look into this for you. You can also call 132 331."
    ),
    EscalationCategory.COMPLAINT: (
        "I'm sorry you've had a frustrating experience. I'll pass you to a Medibank consultant who can "
        "help resolve this. You can also call 132 331."
    ),
    EscalationCategory.MEDICAL_ADVICE: (
        "I can't give medical advice. Please speak with your doctor or health professional. I can help "
        "with questions about what your Medibank cover includes."
    ),
    EscalationCategory.OUT_OF_SCOPE: (
        "I can only help with questions about Medibank health insurance membership and cover, based on "
        "the Fund Rules and Member Guide."
    ),
    EscalationCategory.LOW_CONFIDENCE: (
        "I couldn't find a clear answer to that in the Fund Rules or Member Guide, so I'll connect you "
        "with a Medibank consultant. You can also call 132 331."
    ),
}

CLASSIFIER_PROMPT = """You route questions sent to Medibank's member support chatbot. The chatbot can \
only answer general questions using Medibank's Fund Rules and Member Guide (waiting periods, what \
hospital/extras/ambulance cover includes, claiming rules, suspending or cancelling, premiums, \
eligibility, and similar policy topics).

Classify the question into exactly one category:
- none: a general policy question the documents could answer. Questions phrased with "I" or "my" are \
still "none" if a general policy answer works (e.g. "Am I covered for physio?", "Can I add my baby?").
- account_specific: needs the member's own records or an action on their account: status of a claim \
or payment, their balance or limits used, changing their details, cancelling or upgrading right now.
- complaint: the member is unhappy, frustrated, or wants to complain or dispute a decision.
- medical_advice: asks for medical or treatment advice (whether to have a procedure, what is wrong \
with them, which treatment is best).
- out_of_scope: unrelated to Medibank health insurance membership (other products, general chat, \
other companies, anything else).

Give a short reason (under 15 words).

Also write search_query: the question rephrased in the terms Medibank's Fund Rules and Member Guide \
would use, so a document search can find the right section. Members often use everyday words, so \
translate them into policy concepts (e.g. "diagnosed after joining" -> pre-existing condition and \
waiting periods; "dentist" -> extras cover dental). Use terms such as hospital cover, extras cover, \
waiting period, pre-existing condition, benefits, limits, claims, premiums, suspension, cancellation."""


class Classification(BaseModel):
    """The JSON shape the classifier must return."""
    category: EscalationCategory = Field(
        description="One of: none, account_specific, complaint, medical_advice, out_of_scope."
    )
    reason: str
    search_query: str = Field(default="", description="The question rephrased in policy terms, for document search.")


# The only categories the LLM classifier may return; EMERGENCY and LOW_CONFIDENCE are set by our code.
CLASSIFIER_CATEGORIES = {
    EscalationCategory.ACCOUNT_SPECIFIC,
    EscalationCategory.COMPLAINT,
    EscalationCategory.MEDICAL_ADVICE,
    EscalationCategory.OUT_OF_SCOPE,
}


def escalate(category: EscalationCategory, reason: str) -> EscalationDecision:
    return EscalationDecision(escalate=True, category=category, reason=reason)


NO_ESCALATION = EscalationDecision(escalate=False)


def check_question(question: str) -> tuple[EscalationDecision, str]:
    """Before retrieval: emergency rules first, then an LLM intent classifier.

    Also returns a search query in policy terms (empty if none), produced by the same LLM call.
    """
    if EMERGENCY_RE.search(question):
        return escalate(EscalationCategory.EMERGENCY, "Question mentions a possible emergency"), ""

    response = get_client().messages.parse(
        model=MODEL,
        max_tokens=1000,
        system=CLASSIFIER_PROMPT,
        messages=[{"role": "user", "content": question}],
        output_config={"effort": "low"},
        output_format=Classification,
    )
    result = response.parsed_output
    if result is None:
        return NO_ESCALATION, ""
    if result.category not in CLASSIFIER_CATEGORIES:
        return NO_ESCALATION, result.search_query
    return escalate(result.category, result.reason), result.search_query


def check_retrieval(chunks: list[RetrievedChunk]) -> EscalationDecision:
    """After retrieval: escalate if no chunk is a real match for the question."""
    best = max((c.semantic_score for c in chunks), default=0.0)
    if best < MIN_SEMANTIC_SCORE:
        return escalate(EscalationCategory.LOW_CONFIDENCE, f"Best document match is weak ({best:.2f})")
    return NO_ESCALATION


def check_answer(answer: Answer) -> EscalationDecision:
    """After answering: escalate if the model says the sources don't support an answer."""
    if answer.confidence < MIN_ANSWER_CONFIDENCE or not answer.citations:
        return escalate(EscalationCategory.LOW_CONFIDENCE, f"Answer confidence is low ({answer.confidence:.2f})")
    return NO_ESCALATION


if __name__ == "__main__":
    from src.retrieval import Retriever

    retriever = Retriever()
    for q in [
        "What is the waiting period for pregnancy?",
        "Am I covered for physio on extras?",
        "Can I add my newborn baby to my policy?",
        "Why was my claim for my dental visit rejected last week?",
        "Please update my bank details for direct debit.",
        "This is ridiculous, I've waited 3 weeks for my refund and nobody calls back!",
        "Should I get knee surgery or try physio first?",
        "What's the weather in Melbourne tomorrow?",
        "I have chest pain and feel dizzy, what should I do?",
        "Does my cover include IVF?",
        "How much does it cost to rent a car in Sydney?",
    ]:
        decision, search_query = check_question(q)
        if not decision.escalate:
            decision = check_retrieval(retriever.retrieve(f"{q} {search_query}"))
        top = max(c.semantic_score for c in retriever.retrieve(q))
        label = decision.category.value if decision.escalate else "answer"
        print(f"{label:<17} sem={top:.2f}  {q}\n{'':<17} {decision.reason}")