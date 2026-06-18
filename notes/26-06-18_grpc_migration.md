# 26-06-18: Architecture Transition to Go Echo & Python gRPC

## Context
During our initial Node.js refactoring exploration, we evaluated the trade-offs of the system architecture under corporate-wide requirements (where **Availability**, **Consistency**, and **Accuracy** are top priorities). 

While Go is the gold standard for availability, Go-native PDF/Docx processing libraries carry a high risk of layout/coordinate bugs for complex templates. We decided to keep the original verified Python PDF parser logic as a stateless microservice and implement the public-facing API Gateway, security middleware, and session vault in Go (Echo framework). The two services communicate over gRPC.

## Reorganized Repository Layout
*   `/gateway`: Go Echo server serving static frontend pages (`/public`) and exposing API REST routes.
*   `/worker`: Python gRPC worker wrapping the legacy PDF processor, Docx templating, and stamp engines.
*   `/proto`: Shared Protocol Buffer (`.proto`) schema files defining the service interface.

## Quick Reference Commands

### Go Code Generation
Run from the repository root:
```bash
nix develop --command protoc --go_out=. --go-grpc_out=. proto/document.proto
```

### Python Code Generation
Run from the repository root:
```bash
nix develop --command uv run --project worker python -m grpc_tools.protoc -I. --python_out=worker/ --grpc_python_out=worker/ proto/document.proto
```

## Legacy POC Reference
The original Streamlit POC code has been frozen and archived in the git branch `poc/streamlit` (pushed to origin) for IT department presentations.
