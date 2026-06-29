# Fix for Unknown PDF ID

## Issue
When parsing `EssentialApplication.pdf`, the application could not extract the metadata or the fields properly because its `pdf_id` was identified as `UNKNOWN_ID`. Conversely, `PrivateApplicationExample.pdf` successfully produced a unique ID. 

The underlying cause was that `EssentialApplication.pdf` lacks an `/ID` field in its PDF trailer array, which `pypdf` relies on when extracting the cryptographic ID.

## Resolution
Modified `worker/src/pdf_processor/utils/pdf_info.py` to add a hashing fallback to `get_pdf_file_id`. When `/ID` is missing from the trailer, the function now computes an MD5 hash of the PDF file stream (`reader.stream.read()`) to generate a consistent and unique identifier for the PDF instead of defaulting to `UNKNOWN_ID`. This ensures that even "anchor of truth" PDFs without standard metadata `/ID` trailers can still correctly participate in structural caching and mapping.
