# Auto-Start Python Worker in integration_test.go

## Overview
When running `go test ./...` in the `gateway` directory, `TestProcessPdf_Integration`, `TestGeneratePdf_Integration`, and `TestGenerateDocx_Integration` previously failed if the Python gRPC server was not manually started beforehand.

## Changes
- Modified `setupTestServer(t)` in `gateway/handlers/integration_test.go` to automatically check if port `50051` is listening.
- If the port is not listening, the test server dynamically spawns the Python gRPC worker (`src/server.py`) using `uv run python`.
- Registers a cleanup hook (`t.Cleanup`) to cleanly terminate the Python process group upon completion of tests.
- If the port is already listening, the existing instance is reused, preventing conflicts.

## Impact
All integration and end-to-end tests now run and pass fully automatically in a single execution of `go test ./...` without requiring manual server orchestration.
