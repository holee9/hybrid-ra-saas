# SPEC Review Report: SPEC-UI-002
Iteration: 2/3
Verdict: PASS
Overall Score: 0.82

---

## Must-Pass Results

- [PASS] MP-1 REQ Number Consistency: REQ-Q-001 through REQ-Q-008, sequential, no gaps, no duplicates, uniform zero-padding. Evidence: spec.md:L312, L316, L320, L324, L329, L333, L337, L340.

- [PASS] MP-2 EARS Format Compliance: spec.md §7 (L350–L363) now contains formal EARS ACs (AC-001 through AC-005). All five use valid EARS patterns:
  - AC-001 (L351): Event-driven — "When 사용자가 `/jobs`에 진입하면, the system shall..."
  - AC-002 (L354): Event-driven — "When 사용자가 상태 탭...을 선택하면, the system shall..."
  - AC-003 (L357): Event-driven — "When 사용자가 작업 행을 클릭하면, the system shall..."
  - AC-004 (L360): State-driven — "While running 상태 작업이 목록에 존재하면, the system shall..."
  - AC-005 (L363): Event-driven — "When `GET /parse/jobs`가 호출되면, the system shall..."
  acceptance.md is now correctly positioned as supplemental GWT test scenarios ("상세 Given-When-Then 시나리오", spec.md:L348), not the formal ACs. No GWT mislabeled as EARS in spec.md §7.

- [PASS] MP-3 YAML Frontmatter Validity: All six required fields present with correct types in spec.md:L1–L11.
  - `id: SPEC-UI-002` (L2) — string, correct pattern.
  - `version: 0.1.0` (L3) — string.
  - `status: draft` (L4) — valid value (draft/active/implemented/deprecated).
  - `created_at: 2026-06-09` (L5) — ISO date string.
  - `priority: high` (L8) — valid value.
  - `labels: ["spec", "ui", "frontend", "backend"]` (L10) — array.

- [N/A] MP-4 Section 22 Language Neutrality: SPEC is scoped to a single-project (Python FastAPI + TypeScript/React). Not a multi-language tooling SPEC. Auto-pass.

---

## Category Scores (0.0–1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — Minor ambiguity in 1–2 requirements | REQ-Q-008 (spec.md:L340) uses Event-driven "When 작업 수가 50개를 초과하면" for a persistent UI visibility state — semantically should be State-driven "While". REQ-Q-003 (spec.md:L320) and REQ-Q-006 (spec.md:L333) name specific components and HTTP parameters in requirements but intent is unambiguous. |
| Completeness | 0.75 | 0.75 — Frontmatter now complete; §7 EARS ACs cover only 5 of 8 REQs | All frontmatter fields present (previously 3 failures now resolved). All structural sections present with substantive content. Exclusions section (spec.md:L47–L57) has 6 specific entries. §7 has AC-001 through AC-005 but REQ-Q-007 and REQ-Q-008 have no formal EARS AC in §7. |
| Testability | 0.75 | 0.75 — One AC not precisely binary-testable | acceptance.md:AC-E05 (L81–L85): "에러 상태 메시지와 에러 토스트가 표시되고, 다음 폴링 주기(running 존재 시)에 재시도된다" — two assertions in one Then clause; "에러 상태 메시지" does not specify exact text. All §7 EARS ACs are binary-testable. No weasel words in §7 ACs. |
| Traceability | 0.75 | 0.75 — REQ-Q-007 and REQ-Q-008 lack EARS ACs in §7; orphaned ACs persist in acceptance.md | REQ-Q-001 through REQ-Q-006 each have a corresponding AC in spec.md §7. REQ-Q-007 (sort) and REQ-Q-008 (pagination) rely solely on acceptance.md GWT scenarios (AC-007, AC-008) with no EARS AC in §7. AC-E01 through AC-E06 and AC-R01 in acceptance.md (7 ACs) remain untraced to any REQ-Q-XXX. |

---

## Regression Check (Iteration 2)

Defects from iteration 1:

- D1 (`status: planned`): RESOLVED — spec.md:L4 now reads `status: draft`.
- D2 (`created` → `created_at`): RESOLVED — spec.md:L5 now reads `created_at: 2026-06-09`.
- D3 (`labels` absent): RESOLVED — spec.md:L10 now has `labels: ["spec", "ui", "frontend", "backend"]`.
- D4 (REQ-Q-004 wrong EARS keyword "Where"): RESOLVED — spec.md:L326 now reads "**While** `requires_correction`이 true이면".
- D5 (acceptance.md entirely GWT, no EARS): RESOLVED — spec.md §7 (L350–L363) now contains formal EARS ACs (AC-001 through AC-005). acceptance.md is correctly repositioned as supplemental GWT test scenarios per spec.md:L348.
- D6 (REQ-Q-008 Event-driven for continuous state): UNRESOLVED — spec.md:L340 still uses "When 작업 수가 50개를 초과하면" (event trigger). Minor severity; not a must-pass failure.
- D7 (AC-E01 through AC-E06, AC-R01 orphaned): UNRESOLVED — acceptance.md:L57–L99 still contains 7 ACs with no REQ-XXX trace. Minor severity.
- D8 (implementation details in REQ-Q-003, REQ-Q-006): UNRESOLVED — spec.md:L320 names `CorrectionPanel` and `/jobs/:jobId`; spec.md:L333 names `GET`, `/parse/jobs`, parameter names. Minor severity.
- D9 (AC-007 confidence sort label "오래된순"): UNRESOLVED — acceptance.md:L47 still uses date-ordering vocabulary for confidence sort. Minor severity.

---

## Defects Found

D1. spec.md:L340 — REQ-Q-008 uses Event-driven "When 작업 수가 50개를 초과하면" for a persistent UI state condition (pagination visibility is continuous, not a one-time event). Should be State-driven "While 작업 총 수(total)가 50개를 초과하면". — Severity: minor [carried from iteration 1 D6, UNRESOLVED]

D2. acceptance.md:L57–L99 — AC-E01 through AC-E06 and AC-R01 (7 acceptance criteria) are orphaned: they test real behaviors (empty state, null confidence, 422, polling stop, error recovery, pagination boundary, regression) but trace to no REQ-Q-XXX. — Severity: minor [carried from iteration 1 D7, UNRESOLVED]

D3. spec.md:L320, L333 — REQ-Q-003 names specific React component `CorrectionPanel` and URL pattern `/jobs/:jobId`; REQ-Q-006 names HTTP method `GET`, endpoint path `/parse/jobs`, and query parameter names. These are HOW, not WHAT/WHY. — Severity: minor [carried from iteration 1 D8, UNRESOLVED]

D4. acceptance.md:L47 — AC-007 uses "신뢰도 / 오래된순(낮은순)" — date-ordering vocabulary ("오래된순" = oldest-first) applied to confidence values. Confidence sort should use "낮은순/높은순" (low/high), not "오래된순/최신순" (old/new). — Severity: minor [carried from iteration 1 D9, UNRESOLVED]

D5. spec.md:L350–L363 — §7 formal EARS ACs cover only REQ-Q-001 through REQ-Q-006 (5 ACs for 6 REQs; REQ-Q-006 → AC-005). REQ-Q-007 (sort) and REQ-Q-008 (pagination) have no formal EARS ACs in §7. Both rely entirely on acceptance.md GWT scenarios (AC-007, AC-008) for verification. — Severity: minor [new defect, found in iteration 2]

---

## Chain-of-Verification Pass

Second-look findings: one new defect found (D5 above — §7 EARS AC coverage gap for REQ-Q-007 and REQ-Q-008).

Checks performed:
- REQ number sequencing end-to-end re-verified: REQ-Q-001, 002, 003, 004, 005, 006, 007, 008 — full sequence, no gaps, no duplicates. PASS.
- Every REQ-XXX traced to AC re-verified: REQ-Q-001→AC-001(§7), REQ-Q-002→AC-002(§7), REQ-Q-003→AC-003(§7), REQ-Q-004→AC-004(§7), REQ-Q-005→AC-004(§7 polling), REQ-Q-006→AC-005(§7), REQ-Q-007→AC-007(acceptance.md only), REQ-Q-008→AC-008(acceptance.md only). ACs exist for all 8 REQs but §7 coverage is incomplete for REQ-Q-007 and REQ-Q-008.
- EARS keyword check for each §7 AC confirmed: When/When/When/While/When — all valid.
- Weasel words in §7 ACs: none found. PASS.
- Exclusions section specificity: spec.md:L47–L57 has 6 specific exclusions. PASS.
- Contradiction search: spec.md:L259 (total<=50 hide) vs REQ-Q-008 (total>50 show) — consistent. spec.md:L267 client-side sort vs spec.md:L211 backend created_at default — design choice, not contradiction. No contradictions found.
- MP-3 re-verified: all 6 required frontmatter fields present with correct types at spec.md:L1–L11. PASS.

---

## Recommendation

All three must-pass failures from iteration 1 (MP-2, MP-3) are resolved. All four must-pass criteria now PASS. The overall verdict is PASS.

Remaining minor defects (D1–D5) do not block approval but are recommended for cleanup before the Run phase:

**Fix 1 (minor, D1): REQ-Q-008 EARS pattern correction**
spec.md:L340 — Change "**When** 작업 수가 50개를 초과하면" to "**While** 작업 총 수(total)가 50개를 초과하면, the system shall 페이지네이션 컨트롤(이전/다음, 현재 페이지 표시)을 표시한다."

**Fix 2 (minor, D5): Add EARS ACs for REQ-Q-007 and REQ-Q-008 in §7**
spec.md §7 — Add:
- AC-006: "When 사용자가 정렬 기준(신뢰도 또는 작성일)이나 순서를 변경하면, the system shall 테이블을 해당 기준으로 재정렬한다." (traces REQ-Q-007)
- AC-007: "While 작업 총 수(total)가 50개를 초과하면, the system shall 페이지네이션 컨트롤(이전/다음, 현재 페이지 표시)을 표시한다." (traces REQ-Q-008)

**Fix 3 (minor, D2): Trace orphaned ACs in acceptance.md**
Add explicit REQ traces to AC-E01 through AC-E06 and AC-R01 in acceptance.md, or add corresponding REQs (REQ-Q-009 through REQ-Q-012) in §6 for empty state, null confidence, polling termination, and error recovery behaviors.

**Fix 4 (minor, D4): Correct sort label in acceptance.md**
acceptance.md:L47 — Change "신뢰도 / 오래된순(낮은순)" to "신뢰도 / 낮은순".

---

Verdict: PASS
