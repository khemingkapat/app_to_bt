import fitz  # PyMuPDF
from PIL import Image


def get_pdf_annotations(pdf_path: str) -> list[dict]:
    """
    Reads a PDF, extracts all annotations, renders their isolated drawings
    to a grayscale pixel matrix (0=black, 255=white), and returns a list of dicts.

    Returns:
        list[dict]: A list of dicts with keys:
            - "page": int (1-indexed page number)
            - "rect": list of floats [x0, y0, x1, y1]
            - "matrix": list of lists of integers (0-255 grayscale values)
    """
    doc = fitz.open(pdf_path)
    annotations = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        for annot in page.annots():
            rect = annot.rect
            if rect.is_empty:
                continue

            # Render only the annotation drawing to grayscale with an alpha channel
            pix = annot.get_pixmap(colorspace=fitz.csGRAY)
            width = pix.width
            height = pix.height
            samples = pix.samples

            # Reconstruct 2D matrix, blending gray values against a white background
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


def save_matrix_to_png(matrix: list[list[int]], output_path: str) -> None:
    """
    Saves a 2D grayscale pixel matrix (list of lists of ints 0-255) to a PNG file.
    """
    height = len(matrix)
    width = len(matrix[0]) if height > 0 else 0
    if width == 0 or height == 0:
        raise ValueError("Matrix cannot be empty.")

    # Flatten the matrix into a single list of pixel values
    flat_data = [pixel for row in matrix for pixel in row]

    # Save using PIL (Pillow)
    img = Image.new("L", (width, height))
    img.putdata(flat_data)
    img.save(output_path)
