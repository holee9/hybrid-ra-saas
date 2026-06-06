"""Document schemas."""
from pydantic import BaseModel


class UploadResponse(BaseModel):
    doc_id: str
    parse_job_id: str
