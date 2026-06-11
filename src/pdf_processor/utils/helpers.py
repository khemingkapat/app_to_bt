from io import BytesIO
from typing import Union
import fitz  # PyMuPDF
from pypdf import PdfReader
from pypdf.generic import IndirectObject


def extract_text_from_coords(pdf_file: Union[str, BytesIO], fields: list[dict], pages_info: list[dict]) -> dict:
    """
    Extracts text from a flattened PDF using structural bounding box coordinates.
    Expects PyPDF-style coordinates (bottom-left origin).
    """
    if isinstance(pdf_file, str):
        doc = fitz.open(pdf_file)
    else:
        pdf_file.seek(0)
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        pdf_file.seek(0)

    # Build map of page heights (1-indexed pages)
    page_heights = {p["page_num"]: p["page_h"] for p in pages_info}
    values_dict = {}

    try:
        for field in fields:
            name = field.get("name")
            widgets = field.get("widgets", [])
            extracted_texts = []

            for widget in widgets:
                page_num = widget.get("page", 1)
                coords = widget.get("coords")
                if not coords or page_num not in page_heights or (page_num - 1) >= len(doc):
                    continue

                pdf_h = page_heights[page_num]
                # Convert from bottom-left origin (PyPDF) to top-left origin (PyMuPDF)
                rect = fitz.Rect(
                    coords["x0"],
                    pdf_h - coords["y1"],
                    coords["x1"],
                    pdf_h - coords["y0"]
                )

                page = doc[page_num - 1]
                text = page.get_text("text", clip=rect).strip()
                if text:
                    extracted_texts.append(text)

            # Combine text if multiple widgets exist for the field (e.g. multi-line or groups)
            if extracted_texts:
                values_dict[name] = " ".join(extracted_texts)
            else:
                values_dict[name] = ""

        return values_dict
    finally:
        doc.close()


def get_word_anchors(pdf_file: Union[str, BytesIO], num_lines: int = 3) -> list[str]:
    """
    Extracts the topmost text lines from the first page of the PDF using PyMuPDF.
    These 'word anchors' can be used to identify a flattened form.
    """
    if isinstance(pdf_file, str):
        doc = fitz.open(pdf_file)
    else:
        # Read from BytesIO, reset pointer first
        pdf_file.seek(0)
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        pdf_file.seek(0)

    try:
        page = doc[0]
        blocks = page.get_text("blocks")
        # Blocks format: (x0, y0, x1, y1, "text", block_no, block_type)
        # Sort blocks vertically top-to-bottom
        blocks.sort(key=lambda b: b[1])

        anchors = []
        for b in blocks:
            text = b[4].strip()
            if text:
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                anchors.extend(lines)
                if len(anchors) >= num_lines:
                    break
        return anchors[:num_lines]
    finally:
        doc.close()


def resolve(obj):
    """Dereference an IndirectObject; pass through everything else."""
    return obj.get_object() if isinstance(obj, IndirectObject) else obj


def rect_to_dict(rect, page_height: float | None = None) -> dict | None:
    """Convert a PDF /Rect array to a coordinate dict with canvas positions."""
    if rect is None:
        return None
    try:
        x0, y0, x1, y1 = (float(v) for v in rect)
        result = {
            "x0": round(x0, 2),
            "y0": round(y0, 2),
            "x1": round(x1, 2),
            "y1": round(y1, 2),
            "width": round(x1 - x0, 2),
            "height": round(y1 - y0, 2),
        }
        if page_height:
            result["canvas_top"] = round(page_height - y1, 2)
            result["canvas_bottom"] = round(page_height - y0, 2)
        return result
    except Exception:
        return None


def get_page_dimensions(pypdf_page) -> tuple[float, float]:
    """Extract page width and height from mediabox or fallback to standard A4."""
    DEFAULT_WIDTH = 595.27
    DEFAULT_HEIGHT = 842.0
    if not pypdf_page or not pypdf_page.mediabox:
        return DEFAULT_WIDTH, DEFAULT_HEIGHT

    width = float(pypdf_page.mediabox[2]) - float(pypdf_page.mediabox[0])
    height = float(pypdf_page.mediabox[3]) - float(pypdf_page.mediabox[1])
    return round(width, 2), round(height, 2)
