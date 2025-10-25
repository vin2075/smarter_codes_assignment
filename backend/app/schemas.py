from pydantic import BaseModel, HttpUrl


class SearchRequest(BaseModel):
 url: HttpUrl
 query: str


class ChunkResult(BaseModel):
 url: str
 chunk_id: str
 html_chunk: str
 tokens: int
 sha256: str
 distance: float | None = None