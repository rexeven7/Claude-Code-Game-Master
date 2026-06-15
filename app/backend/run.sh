#!/bin/bash
# Backend: uv run uvicorn main:app --reload --port 8000   (from app/backend)
cd "$(dirname "$0")"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
