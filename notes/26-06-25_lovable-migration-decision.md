# Lovable Migration Decision

**Date:** 2025-06-25  
**Decision:** Pivot from Go+Python stack to Lovable-native (Path A: full in-browser)

## Context
- Go+Python Phase 1 (Worker) and Phase 2 (Gateway) are complete
- Phase 3 (Infrastructure) and Phase 4 (QA) are skipped — superseded by this migration
- Company uses Lovable for many other projects; native alignment is preferred
- All 8 Python PDF operations confirmed portable to Node.js/TypeScript

## Architecture
- **Frontend:** React + Vite + TypeScript (Lovable-hosted)
- **PDF Processing:** `pdf-lib` + `mupdf.js` (WASM, in-browser)
- **DOCX Generation:** `docxtemplater` + `pizzip` (in-browser)
- **Backend:** Supabase (Auth, PostgreSQL, Storage) — no custom server
- **Retired:** Go gateway, Python worker, gRPC/Protobuf, Docker

## Production Scope
1. PDF → BlueTable Mapping (core)
2. Signature Gateway
3. Config Manager
4. Internal E-Form

## Phases
- Phase 0: mupdf.js PoC (go/no-go gate for flattened PDF extraction)
- Phase 1: Core engine port (Python → TypeScript)
- Phase 2: Lovable UI build (4 pages via AI editor)
- Phase 3: Supabase integration (DB + Storage replace JSON files)

## Risk
- Phase 0 is the gate — if mupdf.js can't handle flattened PDF coord-based text extraction, fall back to Path B (lightweight Node.js API)
