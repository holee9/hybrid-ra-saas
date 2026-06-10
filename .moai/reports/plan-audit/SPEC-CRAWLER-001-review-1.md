# SPEC Review Report: SPEC-CRAWLER-001
Iteration: 1/3
**Verdict: FAIL**
Overall Score: 0.42

---

## Must-Pass Results

### MP-1: REQ Number Consistency — FAIL

REQ numbers are NOT sequential in document order. The document presents: 001, **003**, 002, 004–011. All 11 numbers exist but the document-order sequence is 001, 003, 002, 004... which constitutes a sequencing violation.

### MP-2: EARS Format Compliance — FAIL

- **REQ-CRAWLER-006**: Bundles 3 distinct normative statements under one Ubiquitous requirement: (a) read robots.txt, (b) not fetch disallowed paths, (c) not exceed 1 req/sec.
- **REQ-CRAWLER-008**: Embeds two independent Event-Driven requirements (POST /crawl/trigger AND GET /crawl/status) under one REQ using "; and when".
- **REQ-CRAWLER-005**: Compounds two behavioral responses under one Unwanted pattern: retry logic AND failure-logging+continue behavior.

### MP-3: YAML Frontmatter Validity — FAIL

- `created_at` field is named `created` instead of `created_at` (spec.md:L5)
- `labels` field is entirely absent

### MP-4: Language Neutrality — PASS (N/A — single-language SPEC)

---

## Category Scores

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Clarity | 0.75 | Compound REQs require interpretation |
| Completeness | 0.75 | Missing labels, wrong created_at field name |
| Testability | 0.75 | AC-006 tests implementation detail, not behavior |
| Traceability | 0.50 | REQ-001, -003, -004, -009 all map to AC-001 (4:1) |

---

## Critical Defects (Must Fix)

**D1.** spec.md — REQ-CRAWLER-003 appears before REQ-CRAWLER-002 in document order. Sequential numbering violated. Fix: swap numbers or reorder sections.

**D2.** spec.md:L5 — `created: 2026-06-10` must be `created_at: 2026-06-10`.

**D3.** spec.md:L1–10 — `labels` field absent. Add `labels: [crawler, cloud-control-plane, regulatory-docs]`.

**D4.** spec.md — REQ-CRAWLER-006 bundles 3 requirements. Split into:
- REQ-CRAWLER-006: robots.txt read before crawling
- REQ-CRAWLER-006b: do not fetch disallowed paths
- REQ-CRAWLER-006c (State-Driven): "While crawling, the crawler shall not exceed 1 req/sec per source."

**D5.** spec.md — REQ-CRAWLER-008 bundles 2 Event-Driven requirements. Split into:
- REQ-CRAWLER-008: POST /crawl/trigger → return job_id
- REQ-CRAWLER-012 (new): GET /crawl/status/{job_id} → return status

## Major Defects (Should Fix)

**D6.** REQ-CRAWLER-005 compounds two responses. Split into retry REQ and failure-continue REQ.

**D7.** REQ-001, -003, -004, -009 all map to AC-001. Dedicated ACs needed or claim corrected.

**D8.** spec.md:L264 states "1:1 대응" but traceability table is many-to-one. Correct the claim.

**D9.** §1 Architecture contains specific class/method names contrary to the stated principle at L51. Either remove or mark §1 as non-normative design reference.
