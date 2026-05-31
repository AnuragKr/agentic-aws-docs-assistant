# Backend — Document Ingestion Service

## Pipeline (`ingestion/pipeline.py`)

```
PDF → PyMuPDF → Text → Heading Extraction → Preprocess → Metadata
  → Hierarchical Chunk → Enrich → Embed → OpenSearch + S3
```

## Stack

| Layer | Library |
|-------|---------|
| PDF parser | **PyMuPDF** (`fitz`) |
| HTML / MD | BeautifulSoup + markdown heading extraction |
| Hierarchy | Font-size heuristics (PDF) or `#` headings (MD/HTML) |
| Chunking | Custom hierarchical chunker + tiktoken |
| Fallback split | LangChain `RecursiveCharacterTextSplitter` (oversized sections only) |
| Embeddings | Strategy + Factory + Singleton |

LangChain is **not** tightly coupled — removing it only affects the fallback splitter.

## Structure

```
ingestion/
├── pipeline.py
├── parsers/          PyMuPDFParser + HtmlParser + MarkdownParser + TextParser
├── preprocessors/    cleanup only
├── chunkers/         HierarchicalChunker
├── enrichers/
├── embeddings/
└── writers/
```

## Run

```bash
cd backend && uv sync
uv run uvicorn main:app --host 127.0.0.1 --port 8000

# Simple CLI
python run_ingestion.py
python run_ingestion.py --max-documents 3
python run_ingestion.py --force-reprocess
```

On **EC2** (OpenSearch VPC access):

```bash
uv run python run_ingestion.py --force-reprocess --max-documents 1
```
