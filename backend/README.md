# Backend — Document Ingestion Service

## Pipeline (`ingestion/pipeline.py`)

```
Load → Docling Parse → Preprocess → Metadata → Chunk → Enrich → Embed → Store
```

## Stack

| Layer | Library |
|-------|---------|
| Primary parser | **Docling** (PDF, HTML, MD) |
| Hierarchy | Docling document structure (not regex) |
| Chunking | Custom hierarchical chunker + tiktoken |
| Fallback split | LangChain `RecursiveCharacterTextSplitter` (oversized sections only) |
| Embeddings | Strategy + Factory + Singleton |

LangChain is **not** tightly coupled — removing it only affects the fallback splitter.

## Structure

```
ingestion/
├── pipeline.py
├── parsers/          DoclingParser + TextParser + Factory
├── preprocessors/    cleanup only (no heading regex)
├── chunkers/         HierarchicalChunker
├── enrichers/
├── embeddings/
└── writers/
```

## Run

```bash
cd backend && uv sync
./scripts/fix_opencv.sh   # EC2/Docker: drop opencv-python (libGL), keep headless
uv run uvicorn main:app --host 127.0.0.1 --port 8000

# Simple CLI
python run_ingestion.py
python run_ingestion.py --max-documents 3
```

On **EC2** (no GUI libs), if you see `libGL.so.1` errors:

```bash
uv pip uninstall opencv-python
# opencv-python-headless is already in pyproject.toml
```
