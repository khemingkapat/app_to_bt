from pypdf import PdfReader
from .helpers import resolve, get_page_dimensions


def get_page_info(reader: PdfReader, obj) -> tuple[int | None, float]:
    """Return (1-based page number, page height) for a field object."""
    DEFAULT_HEIGHT = 842.0
    page_ref = obj.get("/P")
    if page_ref is not None:
        page_obj = resolve(page_ref)
        for i, p in enumerate(reader.pages):
            if (
                p.indirect_reference
                and page_obj.indirect_reference == p.indirect_reference
            ):
                _, h = get_page_dimensions(p)
                return i + 1, h

    try:
        pages = reader.get_pages_showing_field(obj)
        if pages:
            idx = reader.pages.index(pages[0])
            _, h = get_page_dimensions(pages[0])
            return idx + 1, h
    except Exception:
        pass

    # Fallback: scan page annotations by name /T (for duplicated or mismapped fields)
    name = obj.get("/T")
    if name:
        name_str = str(name)
        for idx, page in enumerate(reader.pages):
            annots = page.get("/Annots")
            if annots:
                for annot_ref in resolve(annots):
                    annot = resolve(annot_ref)
                    if str(annot.get("/T")) == name_str:
                        _, h = get_page_dimensions(page)
                        return idx + 1, h

    return None, DEFAULT_HEIGHT



def get_pdf_file_id(reader: PdfReader) -> str:
    """Extract the permanent unique cryptographic ID from the PDF trailer."""
    try:
        trailer = reader.trailer
        if "/ID" in trailer:
            id_array = trailer["/ID"]
            raw_id = id_array[0]
            if hasattr(raw_id, "original_bytes"):
                return raw_id.original_bytes.hex()
            if isinstance(raw_id, bytes):
                return raw_id.hex()
            return str(raw_id)
    except Exception:
        pass
    return "UNKNOWN_ID"
