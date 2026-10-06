import pytest

from src.chunking import RULE, SUB, TOP, build_chunks, clean_heading, heading_level, split_long
from src.ingest import clean_text, is_noise
from src.models import DocName, Line


def test_clean_text_removes_control_characters_and_tabs():
    assert clean_text("1.\t \x07that a person") == "1. that a person"


@pytest.mark.parametrize("text", ["6  |  Fund Rules", "Member Guide  |  21", "42"])
def test_page_headers_and_numbers_are_noise(text):
    assert is_noise(text)


def test_real_content_is_not_noise():
    assert not is_noise("A6 No Improper Discrimination.")


@pytest.mark.parametrize("size, bold, expected", [
    (18.0, True, TOP),     # Part / chapter heading
    (11.0, True, RULE),    # Fund Rules rule, e.g. "A6 ..."
    (9.0, True, SUB),      # sub-rule or Member Guide section
    (7.8, True, None),     # bold term inside body text
    (7.8, False, None),    # body text
])
def test_heading_level_from_font(size, bold, expected):
    line = Line(doc=DocName.FUND_RULES, page=1, text="x", size=size, bold=bold)
    assert heading_level(line) == expected


def test_clean_heading():
    assert clean_heading("C | Membership.") == "C Membership"


def test_split_long_keeps_short_text_whole_and_splits_long_text():
    assert split_long("short", max_chars=100) == ["short"]
    parts = split_long("A sentence here. " * 50, max_chars=200)
    assert len(parts) > 1
    assert all(len(p) <= 200 for p in parts)


def test_real_documents_chunk_with_citation_metadata():
    chunks = build_chunks()
    assert len(chunks) > 200
    assert {c.doc for c in chunks} == set(DocName)
    assert all(c.section and c.page >= 1 for c in chunks)
    assert len({c.chunk_id for c in chunks}) == len(chunks)   # ids are unique
    assert any("Having a baby" in c.section for c in chunks)
