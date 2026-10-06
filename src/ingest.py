"""Extract clean, font-annotated lines of text from the source PDFs."""

import re
from pathlib import Path

import pymupdf

from src.models import DocName, Line

RAW_DIR = Path("data/raw")
PDFS = {
    DocName.FUND_RULES: "mpl-fund-rules.pdf",
    DocName.MEMBER_GUIDE: "resident-member-guide.pdf",
}

# Page headers look like "6  |  Fund Rules" or "Member Guide  |  21".
HEADER_RE = re.compile(r"^(\d+\s*\|\s*(Fund Rules|Member Guide)|(Fund Rules|Member Guide)\s*\|\s*\d+)$")
BOLD_FONTS = ("Bold", "SemiBold", "Medium")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f]")
SPACE_RE = re.compile(r"\s+")

def clean_text(text: str) -> str:
    """Remove invisible control characters and collapse runs of whitespace."""
    text = CONTROL_RE.sub("", text)
    return SPACE_RE.sub(" ", text).strip()

def is_noise(text: str) -> bool:
    """True for lines that carry no content: page headers and bare page numbers."""
    return bool(HEADER_RE.match(text)) or text.isdigit()


def extract_lines(pdf_path: Path, doc: DocName) -> list[Line]:
    """Read a PDF into Line objects, one per visual line, skipping noise."""
    lines: list[Line] = []
    with pymupdf.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf, start=1):
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    spans = line["spans"]
                    text = clean_text("".join(s["text"] for s in spans))
                    if not text or is_noise(text):
                        continue
                    lines.append(Line(
                        doc=doc,
                        page=page_num,
                        text=text,
                        size=round(max(s["size"] for s in spans), 1),
                        bold=any(f in s["font"] for s in spans for f in BOLD_FONTS),
                    ))
    return lines


def load_all() -> list[Line]:
    """Extract lines from every source PDF."""
    lines: list[Line] = []
    for doc, filename in PDFS.items():
        lines.extend(extract_lines(RAW_DIR / filename, doc))
    return lines


if __name__ == "__main__":
    all_lines = load_all()
    for doc in DocName:
        print(doc.value, sum(l.doc == doc for l in all_lines), "lines")

    for doc, page in [(DocName.FUND_RULES, 6), (DocName.MEMBER_GUIDE, 26)]:
        print(f"\n===== {doc.value} page {page} =====")
        for l in all_lines:
            if l.doc == doc and l.page == page:
                print(f"{l.size:>5} {'B' if l.bold else ' '}  {l.text}")