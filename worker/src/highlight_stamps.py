#!/usr/bin/env python3
import os
import argparse
from pathlib import Path
import fitz  # PyMuPDF

def highlight_pdf_annotations(input_path: str, output_path: str = None) -> str:
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input PDF not found: {input_path}")

    if not output_path:
        # Default output path under outputs/ directory
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{input_path.stem}_highlighted{input_path.suffix}"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Opening PDF: {input_path}")
    doc = fitz.open(input_path)
    
    total_annotations = 0
    total_stamps = 0

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        annots = list(page.annots())
        if not annots:
            continue

        print(f"Page {page_idx + 1}: Found {len(annots)} annotations")
        for annot in annots:
            total_annotations += 1
            rect = annot.rect
            annot_type_id, annot_type_name = annot.type
            info = annot.info
            
            # Determine coloring based on subtype
            is_stamp = (annot_type_name.lower() == "stamp")
            
            if is_stamp:
                total_stamps += 1
                color = (1, 0, 0)  # Red for stamps
                fill_color = (1, 0.8, 0.8)
                label_prefix = "STAMP"
            else:
                color = (0, 0, 1)  # Blue for other annotations
                fill_color = (0.8, 0.8, 1)
                label_prefix = annot_type_name.upper()

            # Draw highlight rectangle with semi-transparent fill
            page.draw_rect(
                rect,
                color=color,
                fill=fill_color,
                width=2,
                overlay=True,
                fill_opacity=0.25
            )

            # Prepare label text
            name = info.get("title") or info.get("name") or ""
            content = info.get("content") or ""
            label_parts = [label_prefix]
            if name:
                label_parts.append(f"by {name}")
            if content:
                # Truncate content if too long
                trunc_content = content[:30] + "..." if len(content) > 30 else content
                label_parts.append(f"({trunc_content})")
            
            label_text = " | ".join(label_parts)

            # Draw a small text background for readability
            text_size = 8
            text_color = (1, 1, 1)
            bg_color = color
            
            # Position label slightly above the rectangle, or inside if at the top boundary
            y_pos = rect.y0 - 4
            if y_pos < 10:
                y_pos = rect.y1 + 10

            page.insert_text(
                fitz.Point(rect.x0, y_pos),
                label_text,
                fontsize=text_size,
                color=bg_color,
                overlay=True
            )
            print(f"  - Highlighted {annot_type_name} at {rect} on page {page_idx + 1}: '{label_text}'")

    doc.save(output_path)
    doc.close()
    print(f"Successfully saved highlighted PDF to: {output_path}")
    print(f"Stats: Highlighted {total_annotations} annotations total ({total_stamps} stamps).")
    return str(output_path)

def main():
    parser = argparse.ArgumentParser(
        description="Highlight stamp and other annotations in a PDF file for development/debugging."
    )
    parser.add_argument("pdf_path", help="Path to the input PDF file.")
    parser.add_argument(
        "-o",
        "--output",
        help="Optional path to save the highlighted PDF. Defaults to outputs/<name>_highlighted.pdf"
    )

    args = parser.parse_args()
    try:
        highlight_pdf_annotations(args.pdf_path, args.output)
    except Exception as e:
        print(f"Error: {e}")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main()
