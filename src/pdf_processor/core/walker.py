from pypdf import PdfReader

from ..utils.helpers import resolve, rect_to_dict
from ..utils.pdf_info import get_page_info

FLAG_RADIO = 1 << 15  # /Ff bit 16 distinguishes radio groups from checkboxes


def walk_fields(reader: PdfReader, fields_array, parent_ft=None) -> list[dict]:
    """Recursively parse the AcroForm tree to extract structural fields."""
    results = []

    for field_ref in fields_array:
        obj = resolve(field_ref)

        ft_raw = obj.get("/FT") or parent_ft
        ft = str(ft_raw) if ft_raw else None

        t = obj.get("/T")
        v = obj.get("/V")
        ff = obj.get("/Ff", 0)
        kids = obj.get("/Kids")

        name = str(t) if t else None
        value = str(v) if v else ""
        flags = int(resolve(ff)) if ff else 0
        is_radio = bool(flags & FLAG_RADIO)

        rect = obj.get("/Rect")
        page_num, page_h = get_page_info(reader, obj)

        # ── Radio Groups ──
        if kids and ft == "/Btn" and is_radio:
            states = obj.get("/_States_", [])
            kid_widgets = []
            for kid_ref in kids:
                kid = resolve(kid_ref)
                kid_rect = kid.get("/Rect")
                kid_page, kid_h_node = get_page_info(reader, kid)
                kid_widgets.append(
                    {
                        "page": kid_page,
                        "coords": rect_to_dict(kid_rect, kid_h_node),
                    }
                )

            results.append(
                {
                    "field_kind": "radio",
                    "name": name or "UNNAMED",
                    "value": value,
                    "page": page_num,
                    "states": [str(s) for s in states],
                    "widgets": kid_widgets,
                }
            )

        # ── Group Nodes ──
        elif kids and ft not in ("/Tx", "/Ch", "/Sig"):
            results.extend(walk_fields(reader, kids, parent_ft=ft))

        # ── Leaf Forms ──
        else:
            if ft == "/Btn":
                kind = "checkbox"
            elif ft == "/Ch":
                kind = "choice"
            elif ft == "/Sig":
                kind = "signature"
            else:
                kind = "text"

            results.append(
                {
                    "field_kind": kind,
                    "name": name or "UNNAMED",
                    "value": value,
                    "page": page_num,
                    "coords": rect_to_dict(rect, page_h),
                }
            )

    return results
