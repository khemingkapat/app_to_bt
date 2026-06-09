from pypdf import PdfReader
from pypdf.generic import IndirectObject


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
