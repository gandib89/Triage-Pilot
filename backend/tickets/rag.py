"""
RAG pipeline: PDF -> text extraction -> recursive chunking -> embeddings ->
storage -> similarity search.

Chunking is recursive/hierarchical (page -> section -> paragraph -> sentence ->
word), targeting ~500-800 tokens per chunk with ~75 tokens of overlap. Every
chunk keeps its provenance: document name, page number, section heading and
chunk index.

Embeddings come from the already-installed Ollama client (mxbai-embed-large),
so no extra ML dependency is needed.

Storage is currently SQLite: vectors live in a JSON column and similarity is a
dot product computed in Python. The schema and the normalise-on-write step are
deliberately pgvector-shaped so the move to PostgreSQL is a field swap
(JSONField -> pgvector.django.VectorField) plus an ORDER BY, not a rewrite.
"""
import os
import re
from operator import mul
from typing import Dict, Iterable, List, Optional

import ollama
from django.db.models import Q
from pypdf import PdfReader

from .models import DocumentChunk

EMBED_MODEL = "mxbai-embed-large"
EMBED_DIM = 1024

# Chunk sizing. No tokenizer is installed, so tokens are estimated at ~4 chars
# per token, which is close enough for English prose to keep chunks inside the
# 500-800 token target band.
CHARS_PER_TOKEN = 4
TARGET_TOKENS = 650      # what a chunk aims for
MAX_TOKENS = 800         # hard split limit before overlap is added
MIN_TOKENS = 40          # below this a chunk carries no useful signal
OVERLAP_TOKENS = 75

TARGET_CHARS = TARGET_TOKENS * CHARS_PER_TOKEN
MAX_CHARS = MAX_TOKENS * CHARS_PER_TOKEN
MIN_CHARS = MIN_TOKENS * CHARS_PER_TOKEN
OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN

# Separators tried in order: paragraph, line, sentence, word, character.
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

_PAGE_NUMBER_LINE = re.compile(r"^[\s\-—–|]*(?:page\s+)?\d+(?:\s*/\s*\d+)?[\s\-—–|]*$", re.I)
_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*[.)]?\s+)?[A-Z0-9][^.!?]*$")


def estimate_tokens(text: str) -> int:
    """Approximate token count (~4 chars per token)."""
    return max(1, round(len(text) / CHARS_PER_TOKEN))


# --------------------------------------------------------------------------
# 1. Text extraction
# --------------------------------------------------------------------------

def extract_pages(pdf_path: str) -> List[str]:
    """Extract cleaned text for each page of a PDF. Index 0 == page 1."""
    reader = PdfReader(pdf_path)
    return [clean_text(page.extract_text() or "") for page in reader.pages]


def clean_text(text: str) -> str:
    """Undo PDF extraction artefacts: hyphen splits, running page numbers,
    ragged whitespace."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Re-join words broken across a line by a hyphen.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t ]+", " ", line).strip()
        if _PAGE_NUMBER_LINE.match(line):
            continue
        lines.append(line)
    text = "\n".join(lines)
    # Collapse runs of blank lines into a single paragraph break.
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# --------------------------------------------------------------------------
# 2. Structure + recursive chunking
# --------------------------------------------------------------------------

def is_heading(line: str) -> bool:
    """Heuristic: short, capitalised, unpunctuated lines act as section titles."""
    line = line.strip().rstrip(":")
    if not line or len(line) > 80 or len(line.split()) > 12:
        return False
    if line.endswith((".", ",", ";")):
        return False
    if not _HEADING.match(line):
        return False
    # A line of prose that merely fits the length limit usually has lowercase
    # sentence shape; require title-ish casing or numbering.
    return line.isupper() or line[0].isdigit() or line.istitle() or _mostly_capitalised(line)


def _mostly_capitalised(line: str) -> bool:
    words = [w for w in re.split(r"\s+", line) if w[:1].isalpha()]
    if not words:
        return False
    capped = sum(1 for w in words if w[0].isupper())
    return capped / len(words) >= 0.6


def split_sections(page_text: str) -> List[Dict]:
    """Split one page into {'section': str, 'text': str} blocks on headings."""
    blocks, section, buf = [], "", []

    def flush():
        body = "\n".join(buf).strip()
        if body:
            blocks.append({"section": section, "text": body})

    for line in page_text.split("\n"):
        if is_heading(line):
            flush()
            buf = []
            section = line.strip().rstrip(":")
        else:
            buf.append(line)
    flush()
    return blocks


def _recursive_split(text: str, max_chars: int, separators: List[str]) -> List[str]:
    """Split text on the coarsest separator that gets pieces under max_chars."""
    if len(text) <= max_chars:
        return [text]
    if not separators:
        return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

    sep, rest = separators[0], separators[1:]
    if sep == "":
        return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

    pieces, buf = [], ""
    for part in text.split(sep):
        candidate = part if not buf else buf + sep + part
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf:
            pieces.append(buf)
            buf = ""
        if len(part) > max_chars:
            pieces.extend(_recursive_split(part, max_chars, rest))
        else:
            buf = part
    if buf:
        pieces.append(buf)
    return pieces


def _merge_to_target(pieces: List[str], target_chars: int) -> List[str]:
    """Glue small adjacent pieces together so chunks land near the target size
    instead of the splitter's arbitrary boundaries."""
    merged, buf = [], ""
    for piece in pieces:
        candidate = piece if not buf else buf + "\n" + piece
        if len(candidate) <= target_chars:
            buf = candidate
        else:
            if buf:
                merged.append(buf)
            buf = piece
    if buf:
        merged.append(buf)
    return merged


def _overlap_tail(text: str, overlap_chars: int) -> str:
    """Last ~overlap_chars of text, cut on a word boundary."""
    if len(text) <= overlap_chars:
        return text
    tail = text[-overlap_chars:]
    space = tail.find(" ")
    return tail[space + 1:] if space != -1 else tail


def chunk_pages(pages: Iterable[str], document_name: str,
                category: Optional[str] = None) -> List[Dict]:
    """Turn extracted page text into ordered, metadata-carrying chunks.

    Overlap is applied within a section only, so a chunk never leaks context
    from an unrelated heading or a different page.
    """
    chunks: List[Dict] = []
    for page_number, page_text in enumerate(pages, start=1):
        if not page_text:
            continue
        for block in split_sections(page_text):
            pieces = _merge_to_target(
                _recursive_split(block["text"], MAX_CHARS, SEPARATORS),
                TARGET_CHARS,
            )
            previous = ""
            for piece in pieces:
                content = piece if not previous else (
                    _overlap_tail(previous, OVERLAP_CHARS) + "\n" + piece)
                previous = piece
                if len(content.strip()) < MIN_CHARS:
                    continue
                chunks.append({
                    "document_name": document_name,
                    "page": page_number,
                    "section": block["section"],
                    "chunk_index": len(chunks),
                    "content": content.strip(),
                    "token_count": estimate_tokens(content),
                    "category": category,
                })
    return chunks


# --------------------------------------------------------------------------
# 3. Embeddings
# --------------------------------------------------------------------------

def _normalise(vector: List[float]) -> List[float]:
    norm = sum(v * v for v in vector) ** 0.5
    return [v / norm for v in vector] if norm else vector


def embed_texts(texts: List[str], model: str = EMBED_MODEL) -> List[List[float]]:
    """Embed texts with Ollama, returned as unit vectors so cosine similarity
    is a plain dot product (and so pgvector can use its cosine ops later)."""
    if not texts:
        return []
    response = ollama.embed(model=model, input=texts)
    return [_normalise(v) for v in response["embeddings"]]


# --------------------------------------------------------------------------
# 4. Indexing
# --------------------------------------------------------------------------

def ingest_pdf(pdf_path: str, document_name: Optional[str] = None,
               category: Optional[str] = None, batch_size: int = 16) -> int:
    """Extract, chunk, embed and store a PDF. Re-ingesting a document replaces
    its existing chunks. Returns the number of chunks stored."""
    document_name = document_name or os.path.basename(pdf_path)
    chunks = chunk_pages(extract_pages(pdf_path), document_name, category)
    if not chunks:
        return 0

    DocumentChunk.objects.filter(document_name=document_name).delete()

    rows = []
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        vectors = embed_texts([c["content"] for c in batch])
        rows.extend(DocumentChunk(embedding=vector, **chunk)
                    for chunk, vector in zip(batch, vectors))

    DocumentChunk.objects.bulk_create(rows, batch_size=200)
    return len(rows)


# --------------------------------------------------------------------------
# 5. Similarity search
# --------------------------------------------------------------------------

def search_chunks(query: str, category: Optional[str] = None,
                  document_name: Optional[str] = None, max_results: int = 5,
                  min_score: float = 0.5) -> List[Dict]:
    """Metadata-filtered similarity search. Returns chunks with a 0-1 score,
    highest first. Returns [] when nothing is indexed or the embedder is down —
    callers are expected to fall back."""
    queryset = DocumentChunk.objects.all()
    if category:
        # An uncategorized document applies to every ticket category; a
        # categorized one is scoped to just that category.
        queryset = queryset.filter(Q(category__isnull=True) | Q(category=category))
    if document_name:
        queryset = queryset.filter(document_name=document_name)
    if not queryset.exists():
        return []

    try:
        query_vector = embed_texts([query])[0]
    except Exception:
        return []

    # ponytail: full table scan, cosine in Python. Fine for a few thousand
    # chunks; swap for `ORDER BY embedding <=> %s LIMIT n` once the table is on
    # PostgreSQL + pgvector.
    scored = []
    for chunk in queryset:
        score = sum(map(mul, query_vector, chunk.embedding))
        if score >= min_score:
            scored.append((score, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [_as_result(chunk, score) for score, chunk in scored[:max_results]]


def _as_result(chunk: DocumentChunk, score: float) -> Dict:
    """Shape a chunk like a KB article so agent prompts can cite it unchanged."""
    location = f"p. {chunk.page}"
    title = f"{chunk.document_name} — {chunk.section} ({location})" if chunk.section \
        else f"{chunk.document_name} ({location})"
    return {
        "id": f"DOC{chunk.pk}",
        "title": title,
        "content": chunk.content,
        "category": chunk.category or "general",
        "relevance_score": round(score * 100),
        "document_name": chunk.document_name,
        "page": chunk.page,
        "section": chunk.section,
        "chunk_index": chunk.chunk_index,
    }
