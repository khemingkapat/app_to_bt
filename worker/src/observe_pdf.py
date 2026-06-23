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

try:
    from pdf_processor.engine import process_pdf, load_registry
except ImportError as e:
    print(f"Error: Could not import pdf_processor.engine. {e}", file=sys.stderr)
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Parse a PDF file and extract its ID and form fields as JSON."
    )
    parser.add_argument("pdf_path", help="Path to the PDF file to observe.")
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
            pdf_id, registry_dict, _ = process_pdf(str(pdf_path), existing_registry=registry)

        # The registry_dict contains the pdf_id as a key
        pdf_data = registry_dict.get(pdf_id, {})
        fields = pdf_data.get("fields", [])

        output = {
            "pdf_id": pdf_id,
            "fields": fields
        }

        # Print clean JSON to stdout
        print(json.dumps(output, indent=4, ensure_ascii=False))

    except Exception as e:
        print(f"Error: An unexpected error occurred during processing: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
