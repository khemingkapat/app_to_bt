# Fix Gateway Assignment Cache Recreation

**Date:** 2026-06-29

## Issue
When `assignment_cache.json` was manually deleted, the system failed to auto-recreate it upon PDF add and manual mapping in the UI.

## Cause
While the Python worker (`cache.py`) had logic to recreate the cache file from `assignment_cache.example.json` if it was missing, the Go gateway (`gateway/handlers/handlers.go`) did not. Since the gateway handles reading the cache to populate the UI mappings, the missing file was silently ignored. The UI received empty mappings and manual mapping operations couldn't merge against a fresh cache file.

## Resolution
Added an `ensureCacheFile` helper function in `gateway/handlers/handlers.go` that mirrors the Python logic. It checks if the cache file exists, and if not, it copies it from `assignment_cache.example.json`. This function is now invoked in all API handlers (`ProcessPdfHandler`, `GeneratePdfHandler`, `GenerateDocxHandler`, `SaveConfigHandler`) before attempting to open the cache file.

Files updated:
- `gateway/handlers/handlers.go`
