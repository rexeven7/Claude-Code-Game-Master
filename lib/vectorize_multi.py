#!/usr/bin/env python3
"""
Vectorize MULTIPLE source documents into ONE campaign RAG index.

The stock `gm-extract.sh prepare` (RAGExtractor) stores chunks with per-document IDs
(doc_0000...), so vectorizing a second book overwrites the first. This helper reuses the
SAME extract -> chunk -> embed pipeline but stores every book's chunks with collision-free
IDs (auto-numbered by the vector store) and per-book provenance, so the whole shelf -
rules, bestiary, campaign - is searchable together.

It only writes to the campaign's vector store; it never touches world-state JSON.

CLI:  vectorize_multi.py <campaign_dir> <file1> [file2 ...]
"""
import sys
from pathlib import Path

# Make both the repo root and lib/ importable regardless of how we're launched.
_HERE = Path(__file__).resolve().parent          # .../lib
_ROOT = _HERE.parent                             # repo root
for _p in (str(_ROOT), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lib.rag.rag_extractor import RAGExtractor


def vectorize_documents(campaign_dir, filepaths, embedder=None, chunk_size=None,
                        reset=True, log=print):
    """Vectorize several documents into one campaign index.

    reset=True clears the index once at the start; each document's chunks are then
    appended with unique IDs and metadata {'document','source_file','chunk_index'}.
    Returns a summary dict.
    """
    rx = RAGExtractor(str(campaign_dir), chunk_size=chunk_size, embedder=embedder)
    store = rx.vector_store

    if reset:
        log("Clearing existing index...")
        store.clear()

    per_doc = []
    for fp in filepaths:
        fp = Path(fp)
        if not fp.exists():
            log(f"  ! skipping (not found): {fp}")
            continue
        log(f"\n=== {fp.name} ===")
        text = rx._extract_text(fp)
        chunks = rx._split_into_chunks(text)
        if not chunks:
            log("  ! no text extracted; skipped")
            continue
        log(f"  {len(text):,} chars -> {len(chunks)} chunks; embedding...")
        embeddings = rx.embedder.embed_batch(chunks, batch_size=32, show_progress=False)
        stem = fp.stem
        metadatas = [{"document": stem, "source_file": str(fp), "chunk_index": i}
                     for i in range(len(chunks))]
        # ids=None -> CampaignVectorStore numbers by current count (collision-free across docs).
        added = store.add_chunks(
            chunks=chunks,
            embeddings=[e.tolist() if hasattr(e, "tolist") else list(e) for e in embeddings],
            metadatas=metadatas,
            ids=None,
        )
        per_doc.append({"document": stem, "chunks": added})
        log(f"  stored {added} chunks (index now {store.count()})")

    return {"campaign_dir": str(campaign_dir),
            "total_chunks": store.count(),
            "documents": per_doc}


def main():
    import json
    if len(sys.argv) < 3:
        print("Usage: vectorize_multi.py <campaign_dir> <file1> [file2 ...]")
        sys.exit(1)
    summary = vectorize_documents(sys.argv[1], sys.argv[2:])
    print("\n" + "=" * 50)
    print(f"Done. {summary['total_chunks']} chunks across {len(summary['documents'])} document(s):")
    for d in summary["documents"]:
        print(f"  - {d['document']}: {d['chunks']}")
    print("JSON:" + json.dumps(summary))


if __name__ == "__main__":
    main()
