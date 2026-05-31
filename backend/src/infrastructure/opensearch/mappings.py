def index_mappings(dimension: int) -> dict:
    """OpenSearch index settings + mappings for knn chunk retrieval."""
    return {
        "settings": {"index": {"knn": True}},
        "mappings": {
            "properties": {
                "chunk_id": {"type": "keyword"},
                "document_id": {"type": "keyword"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dimension,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "nmslib",
                    },
                },
                "content": {"type": "text"},
                "chunk_summary": {"type": "text"},
                "document_type": {"type": "keyword"},
                "service": {"type": "keyword"},
                "service_category": {"type": "keyword"},
                "section": {"type": "keyword"},
                "subsection": {"type": "keyword"},
                "hierarchy_path": {"type": "keyword"},
                "services": {"type": "keyword"},
                "source_file": {"type": "keyword"},
                "title": {"type": "keyword"},
                "document_title": {"type": "keyword"},
                "chapter": {"type": "keyword"},
                "best_practice_id": {"type": "keyword"},
                "best_practice_title": {"type": "keyword"},
                "source_url": {"type": "keyword"},
                "prev_chunk_id": {"type": "keyword"},
                "next_chunk_id": {"type": "keyword"},
                "page_number": {"type": "integer"},
                "chunk_order": {"type": "integer"},
                "total_pages": {"type": "integer"},
                "keywords": {"type": "keyword"},
                "topics": {"type": "keyword"},
                "heading_level": {"type": "integer"},
                "chunk_index": {"type": "integer"},
                "total_chunks": {"type": "integer"},
                "content_type": {"type": "keyword"},
            }
        },
    }
