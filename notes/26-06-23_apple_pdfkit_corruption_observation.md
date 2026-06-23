# Apple PDFKit Form Field Corruption & Metadata Identification

## 1. Apple PDFKit Corruption Findings
When a PDF is filled or saved using **Apple's PDFKit / AnnotationKit** (such as macOS Preview, iOS Markup, or Apple Books), several structural issues commonly occur:
- **Missing `/Ff` (Field Flags)**: It strips the `/Ff` field flag from parent buttons/radio groups (like `CHPLAN 01` to `CHPLAN 08`), making libraries like `pypdf` process them as `UNNAMED` checkboxes.
- **Visual Annotations (`/Stamp`)**: Users drawing checkmarks on standard forms create `/Stamp` (or `/Ink`) annotations instead of mutating field values (`/V`).
- **Malformed Cross-Reference Table**: The writer creates wrong object offsets, leading to warning logs (`Ignoring wrong pointing object ...`) and broken/null page mappings.

---

## 2. How to Identify the PDF Editor / Modifier Programmatically

### A. Checking Vendor-Specific Keys in Annotations
Apple's PDFKit leaves a signature key `/AAPL:AKExtras` (Apple Annotation Kit Extras) in the annotation dictionary when modifying a field or adding annotations:
```python
# Check if an annotation has Apple Markup specific markers
annot_dict = annot_ref.get_object()
if "/AAPL:AKExtras" in annot_dict:
    print("This PDF was modified using Apple PDFKit / Markup")
```

### B. Checking PDF Document Metadata
Most PDF writers add metadata under the `/Info` dictionary. In Python, you can retrieve it via `reader.metadata`:
```python
from pypdf import PdfReader

reader = PdfReader("example.pdf")
metadata = reader.metadata

producer = metadata.get("/Producer") # e.g., "macOS Version 14.5 (Build 23F79) Quartz PDFContext"
creator = metadata.get("/Creator")   # e.g., "Preview" or "Apple PDFKit"
```

---

## 3. How the PDF ID is Retrieved
Every PDF document conforming to specifications is initialized with a permanent unique cryptographic ID. This ID is located in the PDF trailer block under the `/ID` key. 

The `/ID` is an array of two byte-strings:
1. `id_array[0]`: A permanent identifier created when the file was first written.
2. `id_array[1]`: A changing identifier updated whenever the file is modified.

In Python, the engine extracts the first ID (permanent) like this:
```python
def get_pdf_file_id(reader: PdfReader) -> str:
    try:
        trailer = reader.trailer
        if "/ID" in trailer:
            id_array = trailer["/ID"]
            raw_id = id_array[0] # Permanent ID
            if isinstance(raw_id, bytes):
                return raw_id.hex()
            return str(raw_id)
    except Exception:
        pass
    return "UNKNOWN_ID"
```
