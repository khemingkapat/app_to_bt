import sys
import os
import json
import argparse
from pathlib import Path
from contextlib import redirect_stdout

# Add worker and worker/src to sys.path for correct imports
worker_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(worker_dir))
sys.path.insert(0, str(worker_dir / "src"))


def clean_coords(fields):
    if isinstance(fields, (str, int)):
        return fields
    if isinstance(fields, list):
        clean_fields = []
        for field in fields:
            clean_fields.append(clean_coords(field))
        return clean_fields

    if isinstance(fields, dict):
        clean_fields = dict()
        for k, v in fields.items():
            if k == "coords":
                continue
            clean_fields[k] = clean_coords((v))
        return clean_fields


try:
    from pdf_processor.engine import process_pdf, load_registry
except ImportError as e:
    print(f"Error: Could not import pdf_processor.engine. {e}", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Parse a PDF file and extract its ID, form fields, and metadata as JSON."
    )
    parser.add_argument("pdf_path", help="Path to the PDF file to observe.")

    # 3 main options
    parser.add_argument(
        "-m",
        "--metadata",
        action="store_true",
        help="Include metadata, Apple markup flags, and stamp annotations."
    )
    parser.add_argument(
        "-f",
        "--fields",
        action="store_true",
        help="Include form fields with coordinates."
    )
    parser.add_argument(
        "-cf",
        "--clean-fields",
        action="store_true",
        help="Include form fields with coordinates cleaned/removed."
    )
    parser.add_argument(
        "-v",
        "--values",
        action="store_true",
        help="Include extracted values mapped with the assignment cache."
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    try:
        # Load the existing registry to support matching for flattened PDFs
        registry = load_registry()

        # Call process_pdf while redirecting its internal stdout prints to stderr
        with redirect_stdout(sys.stderr):
            pdf_id, registry_dict, values_dict = process_pdf(
                str(pdf_path), existing_registry=registry
            )

        # The registry_dict contains the pdf_id as a key
        pdf_data = registry_dict.get(pdf_id, {})
        fields = pdf_data.get("fields", [])

        # Determine output parts based on flags
        # If no flags are provided, show metadata, original fields, and mapped values by default
        show_default = not (args.metadata or args.fields or args.clean_fields or args.values)
        include_metadata = args.metadata or show_default
        include_fields = args.fields or args.clean_fields or show_default
        clean = args.clean_fields
        include_values = args.values or show_default

        if include_fields and clean:
            fields = clean_coords(fields)

        output = {
            "pdf_id": pdf_id
        }

        if include_metadata:
            # Extract extra PDF metadata and annotations
            from pypdf import PdfReader
            reader = PdfReader(str(pdf_path))
            
            meta = reader.metadata
            metadata_dict = {}
            if meta:
                for key, val in meta.items():
                    clean_key = key.lstrip("/")
                    metadata_dict[clean_key] = str(val) if val else None

            has_apple_markup = False
            stamps = []
            for page_idx, page in enumerate(reader.pages):
                annots = page.get("/Annots")
                if annots:
                    annots = annots.get_object()
                    for annot_ref in annots:
                        try:
                            annot = annot_ref.get_object()
                            if "/AAPL:AKExtras" in annot:
                                has_apple_markup = True
                            subtype = annot.get("/Subtype")
                            if subtype == "/Stamp":
                                rect = annot.get("/Rect")
                                stamps.append({
                                    "page": page_idx + 1,
                                    "name": str(annot.get("/T")) if annot.get("/T") else None,
                                    "rect": [float(x) for x in rect] if rect else None
                                })
                        except Exception:
                            pass
            
            output["metadata"] = metadata_dict
            output["has_apple_markup"] = has_apple_markup
            output["stamps"] = stamps

        if include_fields:
            output["fields"] = fields

        if include_values:
            cache_data = {}
            cache_path = Path("outputs/assignment_cache.json")
            if cache_path.exists():
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        cache_data = json.load(f)
                except Exception:
                    pass
            
            pdf_cache = cache_data.get(pdf_id)
            if not pdf_cache:
                pdf_cache = cache_data.get("UNKNOWN_ID", {})
            field_mappings = pdf_cache.get("field_mappings", {})

            mapped_values = {}
            for f_name, f_val in values_dict.items():
                mapping = field_mappings.get(f_name)
                if mapping:
                    if isinstance(mapping, dict) and "bt_key" in mapping:
                        mapped_field = mapping["bt_key"]
                    else:
                        mapped_field = str(mapping)
                    mapped_values[f_name] = [f_val, mapped_field]
                else:
                    mapped_values[f_name] = [f_val]
            
            output["values"] = mapped_values

        # Print clean JSON to stdout
        print(json.dumps(output, indent=4, ensure_ascii=False))

    except Exception as e:
        print(
            f"Error: An unexpected error occurred during processing: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
