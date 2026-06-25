# WP4-1-3: Secure Signature & Identity Verification E2E Tests

## Overview
This work package implements end-to-end integration tests for the secure signature and identity verification flow in the Gateway service. It ensures that identity verification gates access to signature stamping and that the vault session state transitions correctly from `pending` to `signed`.

## Implementation Details

### 1. Authorization for `StampSignatureHandler`
The `StampSignatureHandler` in `gateway/handlers/handlers.go` was updated to enforce identity verification. It now requires:
- `token`: A valid session token from the vault.
- `identity_id`: The customer's ID number, which must match the one stored in the vault session.

If either is missing or invalid, the handler returns `401 Unauthorized` or `403 Forbidden` respectively.

### 2. Integration Tests
A new test file `gateway/handlers/signature_integration_test.go` was created to verify the entire flow:
- **Identity Verification Gate**: Tests that `POST /api/vault/verify-identity` correctly accepts valid IDs and rejects invalid ones.
- **Unauthorized Stamping**: Verifies that `POST /api/stamp-signature` rejects requests without a valid session token.
- **Authorized Stamping**: Verifies that `POST /api/stamp-signature` succeeds when provided with a valid token and matching ID.
- **Full Signing Flow**: Tests `POST /api/vault/sign`, which performs identity verification, generates a pre-filled PDF via the worker, stamps the signature, generates a DOCX, and updates the vault session status to `signed`.

### 3. Unit Test Updates
Existing tests in `gateway/handlers/handlers_test.go` were updated to provide the necessary authorization parameters for `TestStampSignatureHandler`.

## Verification Results
- All gateway tests passed: `go test ./gateway/...`
- Verified that `StampSignatureHandler` correctly rejects unauthorized requests.
- Verified that the full signing flow correctly transitions the vault state.
