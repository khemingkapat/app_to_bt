import socket
from io import BytesIO
import fitz

def get_network_ip() -> str:
    """Gets the local IP address of the machine on the network."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def stamp_signature_on_pdf(
    pdf_bytes: bytes,
    sig_img_bytes: bytes,
    pdf_id: str = None,
    registry_dict: dict = None,
) -> bytes:
    """Stamps the PNG signature image onto the PDF page matching Text94 or last page as fallback."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    page_idx = None
    rect = None

    if registry_dict and pdf_id:
        entry = registry_dict.get(pdf_id, {})
        fields = entry.get("fields", [])
        for field in fields:
            if field.get("name") == "Text94":
                coords = field.get("coords", {})
                page_num = field.get("page", 5)
                canvas_top = coords.get("canvas_top")
                canvas_bottom = coords.get("canvas_bottom")
                x0 = coords.get("x0")
                x1 = coords.get("x1")
                if all(v is not None for v in [canvas_top, canvas_bottom, x0, x1]):
                    page_idx = page_num - 1
                    if 0 <= page_idx < len(doc):
                        # Scale down by 25% and shift up by 10% of the canvas height
                        h = canvas_bottom - canvas_top
                        rect = fitz.Rect(
                            x0 + 19,
                            canvas_top - 11 - (0.10 * h),
                            x1 - 19,
                            canvas_bottom + 21 - (0.10 * h),
                        )
                        break
                    else:
                        page_idx = None

    if page_idx is None or rect is None:
        page_idx = len(doc) - 1
        page = doc[page_idx]
        width = page.rect.width
        height = page.rect.height
        x0 = width * 0.58
        y0 = height * 0.76
        x1 = width * 0.88
        y1 = height * 0.86
        rect = fitz.Rect(x0, y0, x1, y1)

    page = doc[page_idx]
    page.insert_image(rect, stream=sig_img_bytes)

    out = BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()
