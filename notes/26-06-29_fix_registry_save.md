# Fix PDF Registry Save in ProcessPdf

**Date:** 2026-06-29

## Issue
When uploading a new PDF via the Gateway UI, the `pdf_registry.json` file was not being updated on disk. The system correctly extracted and highlighted fields in the UI, but those structures were never saved.

## Cause
The gRPC `ProcessPdf` handler in the Python backend (`worker/src/server.py`) was calling `process_pdf()` directly. While `process_pdf()` performs all the necessary extraction and layout calculation (which is why highlighting worked in the UI), it does not save the results to disk. The saving logic exists in a wrapper function called `update_pdf_registry()`.

## Resolution
Changed `ProcessPdf` in `worker/src/server.py` to call `update_pdf_registry()` instead of `process_pdf()`. This ensures that after the PDF is processed, the structural mapping and registry updates are safely written back to `outputs/pdf_registry.json`.

Files updated:
- `worker/src/server.py`
