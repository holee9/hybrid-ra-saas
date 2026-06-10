# SPEC Review Report: SPEC-CRAWLER-001
Iteration: 2/3
**Verdict: FAIL**
Overall Score: 0.72

## Regression: All 9 D1–D9 from iteration 1 RESOLVED except partial D7

## Remaining Defects

**D1 (CRITICAL — MP-2):** spec.md:L175–L177 — REQ-CRAWLER-003 uses hybrid EARS `While [state], if [condition], then [system] shall`.
Fix: Split into (a) Event-Driven "When the crawler fetches a document, it shall compute SHA-256 hash" + (b) Unwanted "If the SHA-256 hash matches existing content_hash, then skip Blob/DB write."

**D2 (MAJOR — Traceability):** REQ-CRAWLER-013 → AC-001 is indirect (AC-001 tests runtime, not Terraform definition).
Fix: Add AC-008 verifying Terraform plan includes Container App Job resource, OR reclassify REQ-CRAWLER-013 as §0.5 HARD constraint.

**D3 (MAJOR — RQ-4):** REQ-CRAWLER-013 has specific resource name `crawler-job` and cron `0 2 * * *`.
Fix: Generalize to "The system shall support scheduled daily execution via a dedicated infrastructure job." Move specifics to §1.

**D4 (MINOR — RQ-4):** REQ-CRAWLER-014 has `Python 3.13`, `uv`, Dockerfile path.
Fix: Generalize to "The crawler shall be packaged as a container image deployable to Azure Container Apps."
