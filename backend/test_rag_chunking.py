"""
Self-check for the RAG chunking logic (tickets/rag.py).

Runs offline - no Ollama, no database.

    python test_rag_chunking.py
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from tickets.rag import (  # noqa: E402
    MAX_TOKENS, MIN_TOKENS, OVERLAP_TOKENS, chunk_pages, clean_text,
    estimate_tokens, is_heading, split_sections,
)

PARAGRAPH = ("Refunds are processed within five business days of approval. "
             "Customers must supply the original invoice number. ") * 60


def test_clean_text():
    raw = "Refund   Pol-\nicy\n\n\n\n12\nContact billing@company.com  "
    assert clean_text(raw) == "Refund Policy\n\nContact billing@company.com"


def test_is_heading():
    assert is_heading("2.1 Refund Eligibility")
    assert is_heading("BILLING AND REFUNDS")
    assert is_heading("Refund Policy:")
    assert not is_heading("Refunds are processed within five business days.")
    assert not is_heading("")


def test_split_sections_keeps_headings():
    page = "Refund Policy\nRefunds take five days.\nEscalation\nCall support."
    sections = split_sections(page)
    assert [s["section"] for s in sections] == ["Refund Policy", "Escalation"]
    assert sections[0]["text"] == "Refunds take five days."


def test_chunk_sizes_and_metadata():
    chunks = chunk_pages([PARAGRAPH, "Escalation Path\n" + PARAGRAPH],
                         "policy.pdf", category="billing")
    assert len(chunks) > 2, "long pages should produce multiple chunks"

    for index, chunk in enumerate(chunks):
        assert chunk["chunk_index"] == index
        assert chunk["document_name"] == "policy.pdf"
        assert chunk["category"] == "billing"
        assert chunk["page"] in (1, 2)
        # Overlap is added after the hard split, so allow for it.
        assert MIN_TOKENS <= chunk["token_count"] <= MAX_TOKENS + OVERLAP_TOKENS, \
            f"chunk {index} is {chunk['token_count']} tokens"

    assert {c["page"] for c in chunks} == {1, 2}
    assert any(c["section"] == "Escalation Path" for c in chunks)


def test_consecutive_chunks_overlap():
    chunks = chunk_pages([PARAGRAPH], "policy.pdf")
    first, second = chunks[0], chunks[1]
    tail = first["content"][-OVERLAP_TOKENS * 2:]
    assert second["content"].startswith(tail[:20]) or tail[:20] in second["content"], \
        "second chunk should repeat the tail of the first"


def test_short_page_is_dropped():
    assert chunk_pages(["12"], "policy.pdf") == []


def test_estimate_tokens():
    assert estimate_tokens("a" * 400) == 100


if __name__ == "__main__":
    for name, case in sorted(globals().items()):
        if name.startswith("test_"):
            case()
            print(f"ok  {name}")
    print("all checks passed")
