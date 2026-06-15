#!/bin/bash
# gm-vectorize-books.sh - Vectorize MULTIPLE source books into ONE campaign RAG index,
# so all books (rules + bestiary + campaign) are searchable together. Reuses the same
# embed/chunk pipeline as `gm-extract prepare`, but stores with collision-free IDs +
# per-book provenance. Only writes the vector store; never touches world-state JSON.
#
# Usage:   bash tools/gm-vectorize-books.sh <campaign-name> <file1> [file2 ...]
# Example: bash tools/gm-vectorize-books.sh forbidden-lands source-material/*.pdf
source "$(dirname "$0")/common.sh"

NAME="$1"; shift
if [ -z "$NAME" ] || [ "$#" -eq 0 ]; then
    echo "Usage: gm-vectorize-books.sh <campaign-name> <file1> [file2 ...]"
    echo "Example: gm-vectorize-books.sh forbidden-lands source-material/*.pdf"
    exit 1
fi

CDIR="$CAMPAIGNS_DIR/$NAME"
if [ ! -d "$CDIR" ]; then
    echo "Error: campaign not found: $CDIR"
    echo "Create it first, or check the name with: bash tools/gm-campaign.sh list"
    exit 1
fi

if ! $PYTHON_CMD -c "import sentence_transformers, chromadb" 2>/dev/null; then
    echo "Error: RAG dependencies not installed."
    echo "Install with: uv sync --extra rag"
    exit 1
fi

echo "Vectorizing $# document(s) into campaign '$NAME' (one shared index)..."
$PYTHON_CMD "$LIB_DIR/vectorize_multi.py" "$CDIR" "$@"
