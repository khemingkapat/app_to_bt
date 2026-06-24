import numpy as np
import fitz
from typing import Union
from io import BytesIO

import os

def extract_pdf_annotations(pdf_file: Union[str, BytesIO]) -> list[dict]:
    """
    Extracts annotations from a PDF file using PyMuPDF (fitz), renders them as a
    grayscale pixel matrix, and returns a list of dictionaries with page, rect, and matrix data.
    """
    try:
        if isinstance(pdf_file, BytesIO):
            pdf_file.seek(0)
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            pdf_file.seek(0)
        else:
            if not isinstance(pdf_file, str) or not os.path.exists(pdf_file):
                return []
            doc = fitz.open(pdf_file)
    except Exception:
        return []

    annotations = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        for annot in page.annots():
            rect = annot.rect
            if rect.is_empty:
                continue

            pix = annot.get_pixmap(colorspace=fitz.csGRAY)
            width = pix.width
            height = pix.height
            samples = pix.samples

            matrix = []
            for y in range(height):
                row = []
                for x in range(width):
                    pixel_idx = y * width + x
                    sample_idx = pixel_idx * 2

                    if sample_idx + 1 < len(samples):
                        gray = samples[sample_idx]
                        alpha = samples[sample_idx + 1]
                        # Alpha blend with white background
                        blended = int(
                            gray * (alpha / 255.0) + 255.0 * (1.0 - alpha / 255.0)
                        )
                    else:
                        blended = 255
                    row.append(blended)
                matrix.append(row)

            annotations.append(
                {
                    "page": page_idx + 1,
                    "rect": [rect.x0, rect.y0, rect.x1, rect.y1],
                    "matrix": matrix,
                }
            )

    doc.close()
    return annotations


def match_annotations_to_choices(pdf_file: Union[str, BytesIO], fields: list[dict]) -> dict[str, str]:
    """
    Determines radio choice selections by calculating pixel overlap between
    annotations and radio group options.
    """
    annotations = extract_pdf_annotations(pdf_file)
    if not annotations:
        return {}

    detected_values = {}
    radio_fields = [f for f in fields if f.get("field_kind") == "radio"]

    for annot in annotations:
        page = annot["page"]
        x0, y0, x1, y1 = annot["rect"]
        mat = np.array(annot["matrix"])
        # Map: 1 for background (>127), 0 for drawing strokes
        bitmap = np.where(mat > 127, 1, 0).astype(np.uint8)

        page_radio_fields = [f for f in radio_fields if f.get("page") == page]

        for field in page_radio_fields:
            field_bounded = False
            group_name = field["name"]
            choices = field.get("widgets", [])
            max_field_val = 0
            max_field_name = ""

            for choice in choices:
                coords = choice.get("coords", {})
                c_x0 = coords.get("x0")
                c_y0 = coords.get("canvas_top")
                c_x1 = coords.get("x1")
                c_y1 = coords.get("canvas_bottom")

                if any(v is None for v in [c_x0, c_y0, c_x1, c_y1]):
                    continue

                # Check bounding box overlap
                x_overlap = (
                    (c_x0 >= x0 and c_x0 <= x1)
                    or (c_x1 >= x0 and c_x1 <= x1)
                    or (c_x0 <= x0 and c_x1 >= x1)
                )
                y_overlap = (
                    (c_y0 >= y0 and c_y0 <= y1)
                    or (c_y1 >= y0 and c_y1 <= y1)
                    or (c_y0 <= y0 and c_y1 >= y1)
                )

                if x_overlap and y_overlap:
                    field_bounded = True
                    # Offset within the matrix coordinate frame
                    bounded_x0 = int(c_x0 - x0)
                    bounded_y0 = int(c_y0 - y0)
                    bounded_x1 = int(c_x1 - x0)
                    bounded_y1 = int(c_y1 - y0)

                    # Clamp to bitmap matrix boundaries
                    h, w = bitmap.shape
                    bounded_x0 = max(0, min(bounded_x0, w))
                    bounded_x1 = max(0, min(bounded_x1, w))
                    bounded_y0 = max(0, min(bounded_y0, h))
                    bounded_y1 = max(0, min(bounded_y1, h))

                    if bounded_x1 > bounded_x0 and bounded_y1 > bounded_y0:
                        choice_bitmap = bitmap[bounded_y0:bounded_y1, bounded_x0:bounded_x1]
                        choice_bitmap_mean = choice_bitmap.mean()
                        if choice_bitmap_mean > max_field_val:
                            max_field_val = choice_bitmap_mean
                            max_field_name = choice.get("choice_value", "")

            if field_bounded and max_field_name:
                detected_values[group_name] = max_field_name

    return detected_values
