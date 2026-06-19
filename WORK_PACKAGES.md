# Work Packages (Migration Project Blueprint)

This document maps out the architecture migration plan into granular, trackable work packages. Each task can be linked to a GitHub Issue for direct handoff to developers (e.g., Jules).

## Status Overview

| Work Package | Title | Owner | Status | GitHub Issue / Link |
| :--- | :--- | :--- | :--- | :--- |
| **WP0** | Pioneer & Architecture Design | Khem / Antigravity | ✅ Done | |
| **WP1** | Protobuf Codegen Verification | Jules / Khem | ✅ Done | |
| **WP2** | Python gRPC Worker Service | Jules | ✅ Done | |
| **WP3** | Go Echo Gateway (Routing & Client) | Jules | 🔲 Ready | |
| **WP4** | Docker Compose & Dev Tooling | Jules / Khem | 🔲 Ready | |

---

## Detailed Breakdown

### WP0: Pioneer & Architecture Design ✅
*   **WP0-1: Project Layout Restructuring**
    *   ✅ Cleaned up old Streamlit artifacts and `src/` cache.
    *   ✅ Created `/proto`, `/gateway` (Go), and `/worker` (Python) directory layout.
*   **WP0-2: Zellij Dev Environment Update**
    *   ✅ Removed Streamlit tab from `dev.kdl`.

---

### WP1: Protobuf Codegen Verification ✅
Confirm shared communication contract definitions for all 3 pathways (PDF to Blue Table, E-Form, Signature Gateway).

*   **WP1-1: Protobuf Interface Contract**
    *   ✅ Interface defined in `proto/document.proto` covering `ProcessPdf`, `GeneratePdf`, `GenerateDocx`, and `StampSignature`.
*   **WP1-2: Output Target Compilation**
    *   ✅ Generated stubs verified under `/gateway/proto/document` (Go) and `/worker/proto` (Python).

---

### WP2: Python gRPC Worker Service ✅
Implement the backend engine to expose logic pathways over gRPC.

*   **WP2-1: gRPC Server Scaffolding (`worker/src/server.py`)** [Issue #28](https://github.com/khemingkapat/app_to_bt/issues/28)
    *   ✅ Set up python gRPC server initialization.
    *   ✅ Register `DocumentServiceServicer` interfaces.
*   **WP2-2: PDF to Blue Table Handler (`ProcessPdf`)** [Issue #32](https://github.com/khemingkapat/app_to_bt/issues/32)
    *   ✅ Integrate `pdf_processor.engine` to parse uploaded PDF layouts and return extracted field data and registry JSON.
*   **WP2-3: E-Form Generator Handlers (`GeneratePdf` / `GenerateDocx`)** [Issue #35](https://github.com/khemingkapat/app_to_bt/issues/35)
    *   ✅ Integrate `blue_table_tools.docx_generator` to process form values and generate outputs.
*   **WP2-4: Signature Stamping Handler (`StampSignature`)** [Issue #37](https://github.com/khemingkapat/app_to_bt/issues/37)
    *   ✅ Integrate `signature_gateway` to stamp signature images on PDFs using structural coordinates.
*   **WP2-5: Integration Testing**
    *   ✅ Add tests to run and verify the gRPC handlers.

---

### WP3: Go Echo Gateway (Routing & Client) 🔲
Implement the client-facing REST API Gateway.

*   **WP3-1: Scaffolding & Echo Server Setup**
    *   Initialize Go module in `/gateway`.
    *   Set up Echo server listening on HTTP port (e.g., `:8080`).
*   **WP3-2: gRPC Client Integration**
    *   Write a Go client connection to establish communication with the Python gRPC worker.
*   **WP3-3: API Route Handlers**
    *   Create `/process-pdf`, `/generate-pdf`, `/generate-docx`, and `/stamp-signature` REST endpoints.
    *   Map incoming HTTP requests to gRPC requests, call the worker, and return HTTP JSON/file responses.
*   **WP3-4: Gateway Integration Tests**
    *   Verify Echo REST endpoints trigger mock/live gRPC worker calls.

---

### WP4: Docker Compose & Dev Tooling 🔲
Orchestrate local services and unify development environments.

*   **WP4-1: Dockerfile for Python Worker**
    *   Create Dockerfile for building and running the Python gRPC server.
*   **WP4-2: Dockerfile for Go Gateway**
    *   Create multi-stage Dockerfile for compiling and running the Go Echo application.
*   **WP4-3: Docker Compose Setup**
    *   Add `docker-compose.yml` to run gateway and worker containers in a shared bridge network.
*   **WP4-4: End-to-End Integration Verification**
    *   Verify request flow: Client ➔ Echo REST ➔ gRPC ➔ Worker ➔ Response.
