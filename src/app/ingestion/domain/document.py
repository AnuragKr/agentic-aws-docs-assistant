from pydantic import BaseModel, Field


class RawDocument(BaseModel):
    key: str
    content: str
    extension: str


class ParsedDocument(BaseModel):
    key: str
    text: str
    extension: str


class SectionNode(BaseModel):
    title: str
    level: int
    content: str = ""
    children: list["SectionNode"] = Field(default_factory=list)


class PreprocessedDocument(BaseModel):
    key: str
    text: str
    extension: str
    sections: list[SectionNode] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    document_name: str
    source_url: str
    service: str | None = None
    document_type: str | None = None
    topics: list[str] = Field(default_factory=list)
