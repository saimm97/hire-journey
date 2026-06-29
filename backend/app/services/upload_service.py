from dataclass import dataclass
from fastapi import UploadFile


class UploadValidationError(Exception):
    """Raised when an uploaded file is invalid."""
    pass

@dataclass(slots=True)
class UploadedPDF:
    """A validated PDF file that can be processed."""

    filename: str
    data: bytes

async def read_pdf_upload(file:UploadFile,*,default_filename:str="upload.pdf",
                          max_bytes=5*1024*1024) -> UploadedPDF:
        filename=file.filename or default_filename
        if not filename.lower().endswith(".pdf"):
            raise UploadValidationError("File must be a PDF")
        data=await file.read()
        if len(data)>max_bytes:
            raise UploadValidationError(f"File exceeds maximum size of {max_bytes} bytes")
        if not data.startswith(b"%PDF"):
            raise UploadValidationError("File does not appear to be a valid PDF")
        return UploadedPDF(filename=filename,data=data)
