import os
import json
from io import BytesIO
from typing import Union
import hashlib
from pypdf import PdfReader
from .utils.helpers import resolve, get_page_dimensions, get_word_anchors, extract_text_from_coords
from .utils.pdf_info import get_pdf_file_id
from .core.walker import walk_fields


REGISTRY_FILE = "./outputs/pdf_registry.json"
VALUES_FILE = "./outputs/extracted_values.json"


def load_registry(registry_path: str = REGISTRY_FILE) -> dict:
    """Helper to load the registry."""
    if os.path.exists(registry_path):
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            print("⚠️ Registry file corrupt or empty. Creating a new one.")
            pass
    return {}

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

            struct_field = json.loads(json.dumps(field))
            struct_field.pop("value", None)
            clean_structural_fields.append(struct_field)

        structural_data = {"pages": pages_list, "fields": clean_structural_fields}
        structural_json = json.dumps(structural_data, sort_keys=True)
        structural_hash = hashlib.sha256(structural_json.encode("utf-8")).hexdigest()

        # Check structural fallback (for prints that kept fields but changed ID)
        if existing_registry:
            for existing_id, existing_data in existing_registry.items():
                if existing_data.get("structural_hash") == structural_hash:
                    print(f"🔄 Structural match found. Falling back to existing ID: {existing_id}")
                    pdf_id = existing_id
                    break

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
            for existing_id, existing_data in existing_registry.items():
                existing_anchors = existing_data.get("word_anchors", [])
                # A flattened PDF might have a slightly different block sequence or miss an exact spacing.
                # So we consider it a match if at least one meaningful word anchor string from the original exists
                # in the newly extracted word_anchors, or vice-versa.
                if existing_anchors and word_anchors:
                    has_match = False
                    for anchor in word_anchors:
                        for existing_anchor in existing_anchors:
                            # A partial match (e.g. one string is inside another) is robust for flattened PDFs
                            if anchor in existing_anchor or existing_anchor in anchor:
                                has_match = True
                                break
                        if has_match:
                            break

                    if has_match:
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
    registry.update(registry_dict)

    # Save both files
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=4, ensure_ascii=False)

    with open(values_path, "w", encoding="utf-8") as f:
        json.dump(values_dict, f, indent=4, ensure_ascii=False)

    print(f"✅ Pure structural fields saved to: {registry_path}")
    print(f"✅ Simple text values dictionary saved to: {values_path}\n" + "=" * 60)

    return pdf_id, registry_dict, values_dict


if __name__ == "__main__":
    TARGET_PDF = "./resources/FilledApplication.pdf"

    if os.path.exists(TARGET_PDF):
        # Now returns dictionaries directly
        pdf_id, reg, vals = update_pdf_registry(TARGET_PDF)
    else:
        print(f"❌ File not found: '{TARGET_PDF}'")
