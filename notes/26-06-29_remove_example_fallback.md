# Remove Fallback to Example JSON Files

**Date:** 2026-06-29

## Issue
When `assignment_cache.json` or `pdf_registry.json` were manually deleted, the system would automatically recreate them by copying the `.example.json` templates. This behavior was undesirable when a completely fresh, empty registry/cache was needed.

## Resolution
Removed the fallback logic that copied `.example.json` files when the main JSON files were missing. Instead, the system now safely creates an empty JSON object (`{}`) when it needs to recreate these files from scratch. This prevents old or example data from unintentionally polluting the state when files are wiped.

Files updated:
- `gateway/handlers/handlers.go`
- `worker/src/blue_table_tools/cache.py`
- `worker/src/pdf_processor/engine.py`
