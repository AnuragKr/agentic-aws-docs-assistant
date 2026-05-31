#!/usr/bin/env python3
"""
Run document ingestion from the backend directory.

  python run_ingestion.py
  python run_ingestion.py --max-documents 3
  python run_ingestion.py --force-reprocess
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ingestion.runner.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
