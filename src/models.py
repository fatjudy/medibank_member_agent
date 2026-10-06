"""Data types shared across the pipeline: ingest -> retrieve -> escalate -> answer -> UI."""

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class DocName(str, Enum):
    """Which source document a piece of text came from."""
    FUND_RULES = "fund_rules"
    MEMBER_GUIDE = "member_guide"

class Line(BaseModel):
    """One line of text extracted from a PDF, with font info for heading detection."""
    doc: DocName
    page: int = Field(ge=1)
    text: str
    size: float
    bold: bool

class EscalationCategory(str, Enum):
    """Why a question is handed to a human (or NONE if the bot can answer)."""
    NONE = "none"
    ACCOUNT_SPECIFIC = "account_specific"
    COMPLAINT = "complaint"
    MEDICAL_ADVICE = "medical_advice"
    OUT_OF_SCOPE = "out_of_scope"
    LOW_CONFIDENCE = "low_confidence"


class Chunk(BaseModel):
    """A section-sized piece of a source PDF, with metadata for citations."""
    chunk_id: str
    doc: DocName
    page: int = Field(ge=1)
    section: str
    text: str


class RetrievedChunk(BaseModel):
    """A chunk returned by search, with its relevance score."""
    chunk: Chunk
    score: float
    semantic_score: float = 0.0


class Citation(BaseModel):
    """A pointer from an answer back to its source."""
    doc: DocName
    page: int = Field(ge=1)
    section: str


class Answer(BaseModel):
    """The LLM's grounded answer."""
    text: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class EscalationDecision(BaseModel):
    """Whether to hand off to a human consultant, and why."""
    escalate: bool
    category: EscalationCategory = EscalationCategory.NONE
    reason: str = ""


class ChatResponse(BaseModel):
    """Everything the UI needs to render one bot turn."""
    message: str
    answer: Answer | None = None
    escalation: EscalationDecision
    sources: list[RetrievedChunk] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_answer_matches_escalation(self) -> "ChatResponse":
        if self.escalation.escalate and self.answer is not None:
            raise ValueError("An escalated response should not include an answer.")
        if not self.escalation.escalate and self.answer is None:
            raise ValueError("A non-escalated response must include an answer.")
        return self
    