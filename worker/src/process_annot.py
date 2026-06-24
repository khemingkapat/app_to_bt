import numpy as np
import sys
import json
import os


sys.path.insert(0, "worker/src")
from extract_annotation_matrix import get_pdf_annotations

annotations = get_pdf_annotations("resources/PrivateApplicationExample.pdf")

first_annot = annotations[0]

page = first_annot["page"]
x0, y0, x1, y1 = first_annot["rect"]
mat = np.array(first_annot["matrix"])

bitmap = np.where(mat > 127, 1, 0).astype(np.uint8)


def is_within(coord, lower, upper):
    return coord >= lower and coord <= upper


file_dir = os.path.dirname(os.path.abspath(__file__))
registry_path = os.path.abspath(
    os.path.join(file_dir, "../../outputs/pdf_registry.json")
)

with open(registry_path, "r") as file:
    data = json.load(file)

data = data["87ba7613a963df438482bbcd8c1612a0"]
radio_fields = [field for field in data["fields"] if field.get("field_kind") == "radio"]

page_radio_fields = [field for field in radio_fields if field.get("page") == page]
# print(json.dumps(radio_fields, indent=2))


for field in page_radio_fields:
    field_bounded = False
    group_name = field["name"]
    choices = field["widgets"]
    max_field_val = 0
    max_field_name = ""
    for choice in choices:
        c_x0, c_y0, c_x1, c_y1 = (
            choice["coords"]["x0"],
            choice["coords"]["canvas_top"],
            choice["coords"]["x1"],
            choice["coords"]["canvas_bottom"],
        )

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
            # Using -x0 and -y0 for correct offsets in the matrix coordinate frame
            bounded_x0 = int(c_x0 - x0)
            bounded_y0 = int(c_y0 - y0)
            bounded_x1 = int(c_x1 - x0)
            bounded_y1 = int(c_y1 - y0)

            choice_bitmap = bitmap[bounded_y0:bounded_y1, bounded_x0:bounded_x1]

            choice_bitmap_mean = choice_bitmap.mean()
            if choice_bitmap_mean > max_field_val:
                max_field_val = choice_bitmap_mean
                max_field_name = choice["choice_value"]

    if field_bounded:
        choice_map = field.get("choices_map", {})
        print(
            f"field {group_name} selected {max_field_name} as {choice_map.get(max_field_name,'')}"
        )
