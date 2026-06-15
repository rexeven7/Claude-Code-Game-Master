#!/bin/bash
# gm-vectorize-books.sh - Vectorize MULTIPLE source books into ONE campaign RAG index,
# so all books (rules + bestiary + campaign + legends) are searchable together. Reuses
# the same embed/chunk pipeline as `gm-extract prepare`, but stores with collision-free
# IDs + per-book provenance. Only writes the vector store; never touches world-state JSON.
#
# Usage:   bash tools/gm-vectorize-books.sh [--append] <campaign-name> <file1> [file2 ...]
#   --append   add these book(s) to the existing index instead of rebuilding it.
# Examples:
#   bash tools/gm-vectorize-books.sh forbidden-lands source-material/*.pdf
#   bash tools/gm-vectorize-books.sh --append forbidden-lands source-material/Forbidden_Lands_Legends.pdf
source "$(dirname "$0")/common.sh"

APPEND=""; REST=()
for a in "$@"; do
    if [ "$a" = "--append" ]; then APPEND="--append"; else REST+=("$a"); fi
done
NAME="${REST[0]}"; FILES=("${REST[@]:1}")

if [ -z "$NAME" ] || [ "${#FILES[@]}" -eq 0 ]; then
    echo "Usage: gm-vectorize-books.sh [--append] <campaign-name> <file1> [file2 ...]"
    exit 1
fi

CDIR="$CAMPAIGNS_DIR/$NAME"
if [ ! -d "$CDIR" ]; then
    echo "Error: campaign not found: $CDIR"
    exit 1
fi
if ! $PYTHON_CMD -c "import sentence_transformers, chromadb" 2>/dev/null; then
    echo "Error: RAG dependencies not installed. Run: uv sync --extra rag"
    exit 1
fi

echo "Vectorizing ${#FILES[@]} document(s) into campaign '$NAME'${APPEND:+ (append mode)}..."
$PYTHON_CMD "$LIB_DIR/vectorize_multi.py" $APPEND "$CDIR" "${FILES[@]}"
