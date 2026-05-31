from typing import Any

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Optional metadata filters applied during vector search."""

    service: str | None = None
    service_category: str | None = None
    section: str | None = None
    subsection: str | None = None
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return not any(
            [
                self.service,
                self.service_category,
                self.section,
                self.subsection,
                self.topics,
                self.keywords,
            ]
        )

    def to_opensearch_clauses(self) -> list[dict[str, Any]]:
        clauses: list[dict[str, Any]] = []
        if self.service:
            clauses.append({"term": {"service": self.service}})
        if self.service_category:
            clauses.append({"term": {"service_category": self.service_category}})
        if self.section:
            clauses.append({"term": {"section": self.section}})
        if self.subsection:
            clauses.append({"term": {"subsection": self.subsection}})
        for topic in self.topics:
            clauses.append({"term": {"topics": topic}})
        for keyword in self.keywords:
            clauses.append({"term": {"keywords": keyword}})
        return clauses
