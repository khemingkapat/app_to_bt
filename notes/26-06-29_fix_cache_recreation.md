# Fix Cache Recreation

**Date:** 2026-06-29

## Issue
When the `pdf_registry.json` and `assignment_cache.json` files were manually deleted, the system failed to recreate them upon adding a new PDF or manual mapping.

## Cause
The path resolution fallback logic in `cache.py` and `engine.py` checked for the existence of the file itself (`os.path.exists(parent_path)`). When the file was deleted, this check evaluated to `False`, causing the system to fall back to the unresolved relative path. Depending on the current working directory (e.g., when run from `worker/`), the file would be recreated in the wrong location instead of the intended root `outputs/` directory.

## Resolution
Modified the path resolution logic to check for the existence of the parent directory (`os.path.exists(os.path.dirname(parent_path))`) instead of the file itself. This ensures that as long as the `outputs/` directory exists, the path correctly resolves to the canonical location and the cache files are properly recreated when missing.

Files updated:
- `worker/src/blue_table_tools/cache.py`
- `worker/src/pdf_processor/engine.py`
