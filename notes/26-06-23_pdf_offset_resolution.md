# PDF Field Offset & Coordinate Mapping Resolution (Apple PDFKit)

## 1. Root Cause Analysis
When PDFs are filled or saved using **Apple's PDFKit / AnnotationKit** (e.g., macOS Preview, iOS Markup, Apple Books), the writer creates duplicate annotation widget objects with new object IDs on the page, but leaves the original field objects in the global `/AcroForm /Fields` array pointing to the old object IDs.

This results in:
- `page` resolving to `null` for fields during parsing.
- Text extraction coordinates failing because page dimensions/context are unavailable.
- Radio buttons failing to align child option coordinates with the correct pages.

---

## 2. Implemented Resolution

### A. Leaf Field Fallback (Name Matching)
Modified [pdf_info.py](file:///home/khemi/workspace/app_to_bt/worker/src/pdf_processor/utils/pdf_info.py) to fall back to scanning all page `/Annots` for a widget with the matching `/T` (field name) if standard page mapping methods return `None`.

### B. Radio Group Fallback (Parent Matching)
Modified [walker.py](file:///home/khemi/workspace/app_to_bt/worker/src/pdf_processor/core/walker.py) to fall back to parent-reference matching if radio group kid widgets cannot resolve their pages. It scans all page annotations to match `/Parent` object IDs and reconstructs active widgets on their correct pages.

---

## 3. Verification & Testing
- Running `observe_pdf.py` on [PrivateApplicationExample.pdf](file:///home/khemi/workspace/app_to_bt/resources/PrivateApplicationExample.pdf) now successfully maps all pages (resolving `1`, `2`, `3`, `4`, `5` instead of `null`).
- Run the full test suite (`pytest`) within the `worker` directory:
  - **43 tests passed, 2 skipped** (no regressions).
