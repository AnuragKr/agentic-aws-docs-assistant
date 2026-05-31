#!/usr/bin/env bash
# rapidocr pulls opencv-python (needs libGL); EC2/Docker use headless instead.
set -euo pipefail
cd "$(dirname "$0")/.."
uv pip uninstall opencv-python 2>/dev/null || true
echo "Using opencv-python-headless only (no libGL.so.1 required)."
