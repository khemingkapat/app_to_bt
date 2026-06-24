import os
import json
import math
import threading
from io import BytesIO
from typing import Union
import hashlib
from pypdf import PdfReader
from .utils.helpers import resolve, get_page_dimensions, get_word_anchors, extract_text_from_coords
from .utils.pdf_info import get_pdf_file_id
from .core.walker import walk_fields


REGISTRY_FILE = "./outputs/pdf_registry.json"
VALUES_FILE = "./outputs/extracted_values.json"

IO_LOCK = threading.RLock()


def load_registry(registry_path: str = REGISTRY_FILE) -> dict:
    """Helper to load the registry."""
    with IO_LOCK:
        if not os.path.exists(registry_path):
            parent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", registry_path))
            if os.path.exists(parent_path):
                registry_path = parent_path

        if not os.path.exists(registry_path):
            example_path = registry_path.replace(".json", ".example.json")
            if os.path.exists(example_path):
                import shutil
                try:
                    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
                    shutil.copy(example_path, registry_path)
                except Exception:
                    pass
        if os.path.exists(registry_path):
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                print("⚠️ Registry file corrupt or empty. Creating a new one.")
                pass
        return {}



def _anchors_match(anchors1: list[str], anchors2: list[str]) -> bool:
    """Check if two sets of word anchors have at least one partial match."""
    if not anchors1 or not anchors2:
        return False
    for a1 in anchors1:
        for a2 in anchors2:
            if a1 in a2 or a2 in a1:
                return True
    return False


def _calculate_center(coords: dict) -> tuple[float, float]:
    """Calculate the (x, y) center of a coordinate dictionary."""
    return (coords["x0"] + coords["x1"]) / 2, (coords["y0"] + coords["y1"]) / 2


def _dist(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def _apply_proximity_matching(reader, raw_fields: list[dict], values_dict: dict):
    """
    Resolves visual annotations (like /Stamp, /Ink) to the nearest form widgets.
    Apple Markup checkmarks are often saved as visual annotations rather than AcroForm values.
    """
    THRESHOLD = 30.0

    # Map target widgets (checkboxes and radio choices) by page for efficient lookup
    # Each entry: {"center": (x, y), "name": str, "kind": str, "choice_value": optional}
    page_widgets = {}

    for field in raw_fields:
        kind = field.get("field_kind")
        name = field.get("name")
        if kind == "checkbox":
            page = field.get("page")
            coords = field.get("coords")
            if page and coords:
                page_widgets.setdefault(page, []).append({
                    "center": _calculate_center(coords),
                    "name": name,
                    "kind": kind
                })
        elif kind == "radio":
            for widget in field.get("widgets", []):
                page = widget.get("page")
                coords = widget.get("coords")
                if page and coords:
                    page_widgets.setdefault(page, []).append({
                        "center": _calculate_center(coords),
                        "name": name,
                        "kind": kind,
                        "choice_value": widget.get("choice_value")
                    })

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        annots = page.get("/Annots")
        if not annots:
            continue

        target_widgets = page_widgets.get(page_num, [])
        if not target_widgets:
            continue

        for annot_ref in resolve(annots):
            annot = resolve(annot_ref)
            subtype = annot.get("/Subtype")

            # Skip /Widget annotations as they are already handled by AcroForm parsing
            if subtype == "/Widget":
                continue

            rect = annot.get("/Rect")
            if not rect:
                continue

            # Calculate center of the visual annotation
            try:
                x0, y0, x1, y1 = [float(v) for v in rect]
                annot_center = ((x0 + x1) / 2, (y0 + y1) / 2)
            except (ValueError, TypeError, IndexError):
                continue

            closest_widget = None
            min_dist = float("inf")

            for widget in target_widgets:
                d = _dist(annot_center, widget["center"])
                if d < min_dist:
                    min_dist = d
                    closest_widget = widget

            if closest_widget and min_dist <= THRESHOLD:
                name = closest_widget["name"]
                kind = closest_widget["kind"]

                # Only update if the field is currently empty or unselected
                current_val = values_dict.get(name, "")
                if not current_val or current_val in ("", "/Off", "Off"):
                    if kind == "checkbox":
                        values_dict[name] = "/Yes"
                    elif kind == "radio":
                        values_dict[name] = closest_widget.get("choice_value", "")


def process_pdf(pdf_file: Union[str, BytesIO], existing_registry: dict = None) -> tuple[str, dict, dict]:
    """
    Parses a PDF file and extracts its structure and values.

    Returns:
        tuple: (pdf_id, registry_dict, values_dict)
    """
    reader = PdfReader(pdf_file)
    pdf_id = get_pdf_file_id(reader)

    # 1. Collect all page sizes
    pages_list = []
    for idx, page in enumerate(reader.pages):
        w, h = get_page_dimensions(page)
        pages_list.append({"page_num": idx + 1, "page_w": w, "page_h": h})

    # 2. Collect raw fields with values
    acroform = reader.trailer.get("/Root", {})
    acroform = resolve(acroform).get("/AcroForm") if acroform else None

    raw_fields = []
    if acroform:
        fields_array = resolve(acroform).get("/Fields", [])
        if fields_array:
            raw_fields = walk_fields(reader, fields_array)

    word_anchors = get_word_anchors(pdf_file)
    values_dict = {}
    clean_structural_fields = []

    # 3. Handle Normal vs. Flattened PDF
    if raw_fields:
        # Normal PDF: Parse fields directly
        for field in raw_fields:
            name = field["name"]
            values_dict[name] = field["value"]

        for field in raw_fields:
            name = field["name"]
            struct_field = json.loads(json.dumps(field))
            struct_field.pop("value", None)

            # Preserve choices_map from existing registry if present
            if existing_registry and pdf_id in existing_registry:
                existing_fields = existing_registry[pdf_id].get("fields", [])
                for ef in existing_fields:
                    if ef.get("name") == name and "choices_map" in ef:
                        struct_field["choices_map"] = ef["choices_map"]
                        break

            clean_structural_fields.append(struct_field)

        structural_data = {"pages": pages_list, "fields": clean_structural_fields}
        structural_json = json.dumps(structural_data, sort_keys=True)
        structural_hash = hashlib.sha256(structural_json.encode("utf-8")).hexdigest()

        # Check for template match in existing registry
        matched_template_id = None
        if existing_registry:
            # 1. Direct ID match (and validate anchors if possible)
            if pdf_id in existing_registry:
                existing_data = existing_registry[pdf_id]
                existing_anchors = existing_data.get("word_anchors", [])
                # If anchors match, we definitely have a template match
                if _anchors_match(word_anchors, existing_anchors):
                    matched_template_id = pdf_id

            # 2. Structural hash fallback
            if not matched_template_id:
                for existing_id, existing_data in existing_registry.items():
                    if existing_data.get("structural_hash") == structural_hash:
                        print(f"🔄 Structural match found. Falling back to existing ID: {existing_id}")
                        matched_template_id = existing_id
                        break

            # 3. Word anchor fallback (for corrupted/modified normal PDFs)
            if not matched_template_id:
                for existing_id, existing_data in existing_registry.items():
                    existing_anchors = existing_data.get("word_anchors", [])
                    if _anchors_match(word_anchors, existing_anchors):
                        print(f"📄 Word Anchor match found for normal PDF! Falling back to ID: {existing_id}")
                        matched_template_id = existing_id
                        break

        # Resolve target fields for proximity matching (use matched template fields if available)
        proximity_target_fields = raw_fields
        if matched_template_id and matched_template_id in existing_registry:
            # Use clean template data instead of newly extracted (potentially corrupted) fields
            pdf_id = matched_template_id
            template_data = existing_registry[pdf_id]
            clean_structural_fields = template_data.get("fields", clean_structural_fields)
            pages_list = template_data.get("pages", pages_list)
            structural_hash = template_data.get("structural_hash", structural_hash)
            proximity_target_fields = clean_structural_fields

        # 4. Proximity matching for visual annotations (Apple Markup support)
        _apply_proximity_matching(reader, proximity_target_fields, values_dict)

        registry_dict = {
            pdf_id: {
                "pages": pages_list,
                "fields": clean_structural_fields,
                "structural_hash": structural_hash,
                "word_anchors": word_anchors,
            }
        }
    else:
        # Flattened PDF: No raw fields, so fallback using word_anchors
        matched = False
        structural_hash = None
        if existing_registry:
            # 1. First, check if the extracted pdf_id exists and validate its anchors
            if pdf_id != "UNKNOWN_ID" and pdf_id in existing_registry:
                existing_data = existing_registry[pdf_id]
                existing_anchors = existing_data.get("word_anchors", [])
                if _anchors_match(word_anchors, existing_anchors):
                    print(f"📄 PDF ID '{pdf_id}' matched in registry with valid anchors.")
                    clean_structural_fields = existing_data.get("fields", [])
                    structural_hash = existing_data.get("structural_hash")
                    matched = True

            # 2. Fallback to full registry anchor scan if ID check failed or anchors mismatched
            if not matched:
                for existing_id, existing_data in existing_registry.items():
                    # Skip the one we already checked by ID
                    if existing_id == pdf_id:
                        continue

                    existing_anchors = existing_data.get("word_anchors", [])
                    if _anchors_match(word_anchors, existing_anchors):
                        print(f"📄 Word Anchor match found for flattened PDF! Falling back to ID: {existing_id}")
                        pdf_id = existing_id
                        clean_structural_fields = existing_data.get("fields", [])
                        structural_hash = existing_data.get("structural_hash")
                        matched = True
                        break

        if matched and clean_structural_fields:
            # Extract text from visual bounding boxes
            values_dict = extract_text_from_coords(pdf_file, clean_structural_fields, pages_list)
            print(f"✨ Extracted {len(values_dict)} fields using visual coordinate mapping.")

        registry_dict = {
            pdf_id: {
                "pages": pages_list,
                "fields": clean_structural_fields,
                "structural_hash": structural_hash,
                "word_anchors": word_anchors,
            }
        }

    # Conditional Annotation-to-Choice Mapping
    meta = reader.metadata or {}
    has_annotation_or_stamp = False
    for key, val in meta.items():
        key_clean = key.lower().lstrip('/')
        val_str = str(val).lower() if val else ""
        if "annotation" in key_clean or "stamp" in key_clean or "annotation" in val_str or "stamp" in val_str:
            has_annotation_or_stamp = True
            break

    if not has_annotation_or_stamp:
        for page in reader.pages:
            annots = page.get("/Annots")
            if annots:
                try:
                    annots_list = resolve(annots)
                    for annot_ref in annots_list:
                        annot = resolve(annot_ref)
                        subtype = str(annot.get("/Subtype", ""))
                        if "/Stamp" in subtype or "/Ink" in subtype or "stamp" in subtype.lower() or "annot" in subtype.lower():
                            has_annotation_or_stamp = True
                            break
                except Exception:
                    pass
            if has_annotation_or_stamp:
                break

    if has_annotation_or_stamp and clean_structural_fields:
        from .annotation_matcher import match_annotations_to_choices
        annot_values = match_annotations_to_choices(pdf_file, clean_structural_fields)
        for name, val in annot_values.items():
            values_dict[name] = val


    return pdf_id, registry_dict, values_dict



def update_pdf_registry(
    pdf_file: Union[str, BytesIO],
    registry_path: str = REGISTRY_FILE,
    values_path: str = VALUES_FILE,
) -> tuple[str, dict, dict]:
    """
    Processes the PDF, saves the structural and extraction records locally,
    and returns both dictionaries for Streamlit UI consumption.
    """
    print(f"🔍 Processing: {pdf_file}")

    # Load or create the big registry file
    registry = load_registry(registry_path)

    pdf_id, registry_dict, values_dict = process_pdf(pdf_file, existing_registry=registry)
    print(f"🔑 ID: {pdf_id}")

    # Update global map entry
    with IO_LOCK:
        # Re-load registry to ensure we don't overwrite other concurrent updates
        registry = load_registry(registry_path)
        registry.update(registry_dict)

        # Save registry file (pure structural data, no personal info)
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=4, ensure_ascii=False)

    print(f"✅ Pure structural fields saved to: {registry_path}")
    print(f"✅ Simple text values dictionary kept in-memory for stateless processing\n" + "=" * 60)

    return pdf_id, registry_dict, values_dict


if __name__ == "__main__":
    TARGET_PDF = "./resources/FilledApplication.pdf"

    if os.path.exists(TARGET_PDF):
        # Now returns dictionaries directly
        pdf_id, reg, vals = update_pdf_registry(TARGET_PDF)
    else:
        print(f"❌ File not found: '{TARGET_PDF}'")
