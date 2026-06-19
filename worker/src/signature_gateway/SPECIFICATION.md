# Signature Gateway — Integration Spec

**Status:** Discussion notes / pre-implementation brief
**Feature name:** Signature Gateway
**Target codebase:** `app-to-bt` (Application-to-BlueTable Unified Intake Workflow)
**Audience:** whoever (human or agent) implements this next — this document describes the *task*, not the *implementer*.

---

## 1. Purpose

The `app-to-bt` repo already produces a pre-filled AcroForm PDF as one of its two converged outputs (see README's pipeline diagram, `PDF_OUT`), explicitly labeled as a **"Truth anchor for wet signature."** That promise — getting the document to a signature — isn't implemented yet. The **Signature Gateway** closes that gap: a lightweight, database-free pathway that takes the already-filled PDF, generates a one-time link, and lets the customer verify their identity and sign on a phone, after which the sales rep is notified that the finished documents are ready to download.

Conceptually this slots in as a new phase after the existing "9a. Review & Export" step in the README pipeline — call it **Phase 6: Signature Gateway**.

## 2. Scope

**In scope:**
- A sales-rep-facing screen to generate a secure, single-use customer link from an already-processed application (PDF + BlueTable data already resolved).
- A mobile-first customer-facing screen, reached via that link, that gates access behind an identity check, shows a summary, and captures a signature.
- Server-side generation of the final filled PDF and filled BlueTable DOCX once the customer signs.
- A best-effort in-app notification back to the sales rep's open session when those documents are ready.
- Keeping the above as stateless as practically possible — no long-term storage of customer PII.

**Out of scope (for this phase):**
- True push notifications that work when the rep's browser tab is closed (would require a service worker + web push backend — real infrastructure, not a POC-shaped addition).
- Multi-process / multi-server deployment of the vault (the in-memory approach described below assumes a single Streamlit process, consistent with the rest of this repo's "database-free" design).
- Replacing or duplicating the existing field-mapping admin UI (`src/pages/pdf_to_blue_table.py`) — this feature consumes its output, it doesn't reimplement it.

## 3. High-Level Flow

### Pathway A — Sales Rep Portal
1. Rep selects/uploads the application PDF as usual (this can literally be the existing PDF→BlueTable flow, or a new lighter screen — see §6 for which functions to call).
2. System extracts structure via the existing extraction pipeline and looks up whether this PDF template already has a saved field mapping.
   - If yes: pull `customer_name` and `identity_id` directly from the resolved BlueTable data (`name`, `id_card_no` keys).
   - If no: this PDF hasn't been taught to the system yet — surface a message pointing the rep to the existing Config Manager / PDF-to-BlueTable admin tools rather than re-implementing that mapping wizard here.
3. Rep clicks "Generate Secure Customer Link." System generates a high-entropy token (`secrets.token_hex()`), creates a `transaction_vault` entry (see §5) keyed by that token, and shows the rep a copyable link (`?token=<token>`).
4. Rep's screen begins lightweight polling of that vault entry's status (see §7) so it can react once the customer signs.

### Pathway B — Mobile Customer Signing Flow
1. Customer opens the link. `st.query_params` routes them straight into the narrow, mobile-optimized signing view (no sales portal UI visible).
2. **Identity gate:** customer enters their ID/passport number into a password-style (masked) input. The entry and the stored truth value are both normalized (strip hyphens, spaces, punctuation, casing) before comparison, so formatting differences don't cause false failures.
3. On a match: show a read-only summary of the pre-filled application fields, then a touch-friendly signature canvas (correct package: `streamlit-drawable-canvas`, not `streamlit_canvas`) sized and configured so finger/stylus drawing doesn't trigger page scroll.
4. On "Submit Secure Signature": the system fills the real PDF and DOCX (see §6) and updates the vault entry's status to `signed`.
5. The raw `identity_id` value is discarded from the vault the moment verification succeeds — it doesn't need to persist past that point.

## 4. Compliance & Statelessness Requirements

The goal is **no retained raw customer PII beyond the life of one transaction**, not "no record of anything happened." Those are different, and worth keeping distinct when this goes to Legal/Compliance:

- `transaction_vault` lives in server memory only — no disk writes of customer name, ID number, or signature image.
- Every vault entry carries a TTL (suggested default: 15–30 minutes, configurable). Entries are purged on TTL expiry regardless of whether they were downloaded.
- Once the identity check passes, the raw ID number is dropped from the vault; it only needs to exist long enough to be baked into the generated PDF/DOCX.
- Once the rep downloads the finished documents (or the TTL lapses), the vault entry — including the generated file bytes — is deleted.
- **Caveat to flag explicitly:** most e-signature compliance frameworks expect *some* retained audit trail (who signed, when, a hash of what was signed, consent language shown). "Stateless" in this spec means no retained PII payload — it should not be read as "no audit trail at all." That's a decision for Legal & Compliance, not an engineering default.
- **Caveat to flag explicitly:** a single national-ID/passport number is not a secret, so this identity gate is a friction/convenience check, not strong authentication. Worth a sentence in the UI disclaimer and a sign-off from Compliance rather than presenting it as a KYC-equivalent control.
- Note: the existing structural caches this repo already writes to disk (`outputs/pdf_registry.json`, `outputs/assignment_cache.json`, `outputs/extracted_values.json`) store field *coordinates and key names*, not customer values — they're safe to keep using as-is and don't conflict with the no-long-term-PII goal.

## 5. Vault Data Model (in-memory only)

| Field | Lifetime | Notes |
|---|---|---|
| `secure_token` | until TTL/download | dict key, `secrets.token_hex()` |
| `pdf_id` | until TTL/download | links back to the registered template |
| `customer_name` | until TTL/download | shown to customer for confirmation |
| `identity_id` | **until verification succeeds, then deleted** | truth value for the gate |
| `bt_data` | until TTL/download | resolved BlueTable fields used to fill outputs |
| `status` | until TTL/download | `pending` → `signed` → (purged) |
| `created_at` / `ttl_seconds` | until TTL/download | drives expiry |
| `signed_pdf_bytes` / `signed_docx_bytes` | until download or TTL | generated only after signing |
| `signed_at` | until TTL/download | for the eventual audit-trail discussion |

## 6. Reuse Map — Don't Re-implement These

The repo already has the extraction/fill logic this feature needs. Nothing here should be rewritten from scratch:

- `src/pdf_processor/engine.py` → `update_pdf_registry(pdf_file)` — structural extraction, returns `(pdf_id, registry_dict, values_dict)`.
- `src/blue_table_tools/cache.py` → `load_cache(pdf_id)` / `save_cache(pdf_id, field_mapping)` / `get_product_config_name(pdf_id)` — existing field-mapping lookups.
- `src/pdf_processor/inverter.py` → `fill_acroform_pdf(input_pdf, customer_data, config_path)` and `map_customer_data_to_pdf(...)` — produces the final stamped PDF.
- `src/blue_table_tools/docx_generator.py` → `fill_blue_table_docx(template_path, data)` (plus `apply_acceptance_rules`, `resolve_plan_combination`) — produces the final BlueTable DOCX.
- `src/blue_table_tools/schema.py` → `BLUETABLE_FIELDS` — the canonical field/label list if the new screens need to render or validate any of these.

**Explicitly not reused as-is:** `src/pages/pdf_to_blue_table.py` is the interactive, field-by-field admin mapping wizard — it's a UI, not a library. The new feature should call the modules above directly, and only point a rep at that page when a PDF genuinely has no saved mapping yet.

### Dependency wiring — depends on where this lives

- **If this feature lives inside the `app-to-bt` repo:** no special wiring needed — just import the modules above directly (`from src.pdf_processor.inverter import fill_acroform_pdf`, etc.).
- **If this feature lives in a separate repo/app:** prefer adding `pdf_processor` / `blue_table_tools` as a proper pinned dependency rather than copying files — e.g. via `uv add` pointing at a git URL with a subdirectory (`git+https://.../app-to-bt.git@main#subdirectory=src`). Git submodule is a lighter-weight alternative if a visible pointer is preferred over a packaged dependency. Git subtree also works (vendors the subdirectory's history into the new repo, pullable later) but is heavier than necessary for a Python import dependency.
- **This decision should be made before implementation starts** — it changes whether there's any dependency-wiring work at all.

## 7. Post-Signature Export & Rep Notification

1. On signature submit, call `fill_acroform_pdf` and `fill_blue_table_docx` using the vault entry's `bt_data` and signature artifact; store the resulting bytes back into the vault entry; flip `status` to `signed`.
2. The rep's portal screen (the one that generated the link) runs a lightweight polling block — e.g. `st.fragment(run_every="3s")` — that checks that token's status in the vault.
3. When status flips to `signed`, that fragment renders the two `st.download_button`s (pulling bytes directly from the vault) and fires an in-page browser notification via injected JS (`Notification` API, permission requested once) so the rep gets an OS-level nudge even if they're not looking at the tab.
4. **Honest limitation to carry forward:** this only works while the rep's tab remains open in that browser session — it is not a real push notification system. If "notify even when the tab/browser is closed" turns out to be a hard requirement, that's a different, heavier feature (service worker + web push backend, or email/SMS), and should be called out as a separate decision rather than assumed.

## 8. Open Questions / Decisions Needed Before Build

- Same repo or separate repo for this feature? (Determines the dependency-wiring approach in §6.)
- What TTL is acceptable for the in-memory vault entries?
- Does Legal/Compliance accept ID-number-only as the customer-facing gate, or is a second factor required?
- Does Compliance require any retained audit record (hash + timestamp + consent text) even though the PII payload itself is ephemeral?
- Is "notification while tab is open" sufficient, or does this eventually need real push/email/SMS delivery?

## 9. Suggested Acceptance Criteria

- No customer PII is written to disk at any point in this flow.
- A vault entry left untouched past its TTL is unrecoverable (no PDF/DOCX, no identity data).
- The identity gate accepts formatting variants (hyphens/spaces/case) of the correct ID and rejects everything else.
- The rep's screen visibly reflects a status change (download buttons appear) without the rep manually refreshing the page.
- The generated PDF and DOCX are produced via the existing `inverter`/`docx_generator` functions, not new parsing/filling logic.
