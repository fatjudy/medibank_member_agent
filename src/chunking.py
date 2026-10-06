"""Group extracted lines into section-sized chunks using font-based heading detection."""

import json
from pathlib import Path

from src.ingest import load_all
from src.models import Chunk, DocName, Line

INDEX_DIR = Path("data/index")
CHUNKS_PATH = INDEX_DIR / "chunks.json"

# Cover, index/contents and back-cover pages carry no policy content.
SKIP_PAGES = {
    DocName.FUND_RULES: {1, 3, 48},
    DocName.MEMBER_GUIDE: {1, 6, 7, 40},
}
MAX_CHARS = 1500

# Heading levels: 0 = Part/Chapter, 1 = Rule (Fund Rules only), 2 = sub-section.
TOP, RULE, SUB = 0, 1, 2


def heading_level(line: Line) -> int | None:
    """Return the heading level of a line, or None if it is body text."""
    if line.size >= 18:
        return TOP
    if line.bold and line.size >= 11:
        return RULE
    if line.bold and line.size >= 9:
        return SUB
    return None


def clean_heading(text: str) -> str:
    """'C | Membership.' -> 'C Membership'"""
    return text.replace(" | ", " ").rstrip(".").strip()


def split_long(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Split text on sentence-ish boundaries into pieces of at most max_chars."""
    if len(text) <= max_chars:
        return [text]
    parts, current = [], ""
    for sentence in text.replace("; ", ";\n").replace(". ", ".\n").split("\n"):
        if current and len(current) + len(sentence) + 1 > max_chars:
            parts.append(current.strip())
            current = ""
        current += sentence + " "
    if current.strip():
        parts.append(current.strip())
    return parts


def chunk_doc(lines: list[Line], doc: DocName) -> list[Chunk]:
    """Turn one document's lines into Chunks, one per lowest-level section."""
    chunks: list[Chunk] = []
    path: list[str] = ["", "", ""]  # current heading text at each level
    body: list[str] = []
    start_page = 1
    prev_level: int | None = None

    def flush() -> None:
        text = " ".join(body).strip()
        if not text:
            return
        section = " > ".join(h for h in path if h) or "Preface"  # text before the first heading
        for part in split_long(text):
            chunks.append(Chunk(
                chunk_id=f"{doc.value}-p{start_page}-{len(chunks):03d}",
                doc=doc,
                page=start_page,
                section=section,
                text=f"{section}\n{part}",
            ))

    for line in lines:
        if line.page in SKIP_PAGES[doc]:
            continue
        level = heading_level(line)

        if level is None:
            if not body:
                start_page = line.page
            body.append(line.text)
        elif level == prev_level and not body:
            # Heading wrapped onto a second line: join it to the previous one.
            path[level] = clean_heading(path[level] + " " + line.text)
        elif level == TOP and clean_heading(line.text) == path[TOP]:
            pass  # running Part/Chapter header repeated on each page
        else:
            flush()
            body = []
            path[level] = clean_heading(line.text)
            for deeper in range(level + 1, len(path)):
                path[deeper] = ""
            start_page = line.page
        prev_level = level

    flush()
    return chunks


def build_chunks() -> list[Chunk]:
    """Chunk every source document."""
    lines = load_all()
    chunks: list[Chunk] = []
    for doc in DocName:
        chunks.extend(chunk_doc([l for l in lines if l.doc == doc], doc))
    return chunks


def save_chunks(chunks: list[Chunk], path: Path = CHUNKS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([c.model_dump(mode="json") for c in chunks], indent=2), encoding="utf-8")


def load_chunks(path: Path = CHUNKS_PATH) -> list[Chunk]:
    return [Chunk(**c) for c in json.loads(path.read_text(encoding="utf-8"))]


if __name__ == "__main__":
    chunks = build_chunks()
    save_chunks(chunks)
    lengths = sorted(len(c.text) for c in chunks)
    for doc in DocName:
        print(doc.value, sum(c.doc == doc for c in chunks), "chunks")
    print(f"length: min {lengths[0]}, median {lengths[len(lengths) // 2]}, max {lengths[-1]}")
    print(f"saved to {CHUNKS_PATH}\n")
    for c in chunks:
        if "aiting period" in c.section:
            print(f"--- {c.chunk_id} | {c.section} (p{c.page})\n{c.text[:300]}\n")
            break