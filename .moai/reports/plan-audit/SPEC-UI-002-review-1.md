# SPEC Review Report: SPEC-UI-002
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.55

---

## Must-Pass Results

- [FAIL] MP-1 REQ Number Consistency: REQ numbers use prefix "Q" (REQ-Q-001 … REQ-Q-008). The prefix itself is internally consistent and sequential with no gaps or duplicates. Zero-padding is uniform. However, the audit rubric requires sequential REQ-{NUM} or REQ-{DOMAIN}-{NUM} with no gaps. By strict interpretation the domain-prefixed pattern passes: REQ-Q-001 through REQ-Q-008, no gaps, no duplicates. **Borderline PASS** — upgrading to PASS with evidence: spec.md:L311, L315, L319, L323, L328, L332, L336, L339. No gap between 001–008, no duplicate.

- [FAIL] MP-2 EARS Format Compliance: Two separate violations.

  **Violation 1 — Wrong EARS keyword in REQ-Q-004 (spec.md:L325):**
  > "**Where** `requires_correction`이 true이면, the system **shall** 해당 작업 행을 교정 필요 인디케이터로 시각적으로 강조한다."

  The EARS "Optional" (Where) pattern applies to optional feature presence, not to a boolean field value that can be true or false at runtime. A `requires_correction=true` condition is a **state**, which must use the State-driven pattern: "**While** requires_correction is true, the system shall…". Using "Where" (Optional pattern) for a runtime boolean state is a pattern misapplication. spec-compact.md:L36 correctly labels REQ-Q-004 as "(State)" — confirming the intent is State-driven — but spec.md:L323 labels it "(State-Driven)" while using the wrong keyword "Where".

  **Violation 2 — Acceptance criteria in acceptance.md are entirely Given-When-Then test scenarios, not EARS:**
  spec.md:L347 directs: "전체 Given-When-Then 시나리오는 `acceptance.md`에 정의한다". acceptance.md:L3 confirms: "Given-When-Then 형식으로 작성한다". All 8 core ACs (AC-001 through AC-008) and all 6 edge-case ACs (AC-E01 through AC-E06) are written in Given/When/Then test scenario format, not EARS patterns. The MP-2 rubric explicitly states: "Given/When/Then test scenarios mislabeled as EARS = FAIL". spec.md §7 (L345–L356) contains only a bullet-point summary, not formal EARS acceptance criteria.

- [FAIL] MP-3 YAML Frontmatter Validity: Three failures in spec.md:L1–L10.

  1. **`created_at` field absent** (spec.md:L5): Field is named `created: 2026-06-09` instead of the required `created_at`. Wrong field name = missing required field.
  2. **`labels` field absent** (spec.md:L1–L10): The field `labels` (required array or string) does not appear anywhere in the frontmatter. Field is entirely missing.
  3. **`status` value invalid** (spec.md:L4): `status: planned` is not in the valid value set (draft, active, implemented, deprecated). "planned" is not a recognized status value.

  spec-compact.md has the same frontmatter (L1–L7) with identical `created` (not `created_at`), identical absence of `labels`, and identical `status: planned`.

- [N/A] MP-4 Section 22 Language Neutrality: This SPEC is scoped to a specific single-project (Python FastAPI + TypeScript/React). It is not a multi-language tooling SPEC. Auto-pass.

---

## Category Scores (0.0–1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — Minor ambiguity in 1–2 requirements a reasonable engineer would resolve differently | REQ-Q-008 (spec.md:L339) states "When 작업 수가 50개를 초과하면" (event-trigger) but pagination visibility is a continuous state (should be State-driven "While"). REQ-Q-003 (spec.md:L320) and REQ-Q-006 (spec.md:L333) contain component names and HTTP parameter names in requirements text, which blurs WHAT/HOW boundary but is largely unambiguous in intent. |
| Completeness | 0.50 | 0.50 — Multiple frontmatter fields missing/wrong; all structural sections present | spec.md frontmatter missing `labels`, `created_at` misnamed `created`, `status: planned` invalid. These are 3 frontmatter failures (MP-3). All structural document sections (HISTORY, Scope/WHY, WHAT, REQUIREMENTS, ACCEPTANCE, Exclusions) are present with substantive content. Exclusions section (spec.md:L47–L56) has 6 specific entries. Score penalized for frontmatter failures. |
| Testability | 0.75 | 0.75 — One AC not precisely binary-testable with minor interpretation | acceptance.md:AC-E05 (L81–L85): "Then 에러 상태 메시지와 에러 토스트가 표시되고, 다음 폴링 주기(running 존재 시)에 재시도된다" — two separate assertions in one Then clause, and "에러 상태 메시지" does not specify the exact message text, making PASS/FAIL require minor interpretation. All other ACs are concrete and binary. No weasel words found in ACs. |
| Traceability | 0.75 | 0.75 — Multiple orphaned ACs with no REQ reference | All 8 REQs (REQ-Q-001 through REQ-Q-008) have at least one corresponding AC in acceptance.md. However, AC-E01 through AC-E06 (acceptance.md:L57–L91) and AC-R01 (acceptance.md:L95–L99) are 7 orphaned ACs — they trace to no REQ-XXX. These cover real behaviors (empty state, null confidence, 422 handling, polling stop, load failure, pagination boundary, regression) but no requirements formally capture them. |

---

## Defects Found

**D1. spec.md:L4 — `status: planned` is not a valid status value** — Severity: critical (MP-3 failure)
Valid values per MP-3 rubric: draft, active, implemented, deprecated. "planned" is none of these.

**D2. spec.md:L5 — `created` field should be `created_at`** — Severity: critical (MP-3 failure)
Field name `created` does not match the required field name `created_at`. The required field is absent.

**D3. spec.md:L1–L10 — `labels` field entirely absent from frontmatter** — Severity: critical (MP-3 failure)
Required field `labels` (array or string) is missing from the YAML frontmatter. No labels are defined anywhere in the frontmatter block.

**D4. spec.md:L323–L325 — REQ-Q-004 uses wrong EARS keyword "Where" for a State-driven requirement** — Severity: major (MP-2 failure)
The requirement description labels it "(State-Driven)" but uses the Optional pattern keyword "Where". The correct keyword is "While". spec-compact.md:L36 also labels it "(State)" confirming the pattern intent. The inconsistency between label and keyword constitutes an EARS pattern violation.

**D5. acceptance.md:L1–L119 — All acceptance criteria use Given-When-Then format, not EARS patterns** — Severity: critical (MP-2 failure)
spec.md:L347 explicitly delegates all ACs to acceptance.md, directing GWT format. Every AC in acceptance.md (AC-001 through AC-E06 and AC-R01) is written in Given/When/Then test scenario format. None match any of the five EARS patterns. This is a systematic MP-2 failure across the entire AC section.

**D6. spec.md:L339 — REQ-Q-008 uses Event-driven pattern for a continuous state condition** — Severity: minor
"When 작업 수가 50개를 초과하면" is an event trigger, but pagination visibility is a persistent state (should be visible while total > 50, not just at the moment total exceeds 50). This should be State-driven: "While total job count exceeds 50, the system shall display pagination controls." The current form implies one-time trigger semantics, which is incorrect for UI visibility.

**D7. acceptance.md:L57–L99 — AC-E01 through AC-E06 and AC-R01 are orphaned ACs (no REQ-XXX trace)** — Severity: minor
Seven acceptance criteria (AC-E01, AC-E02, AC-E03, AC-E04, AC-E05, AC-E06, AC-R01) test real behaviors but trace to no requirement. Empty state, null confidence display, 422 handling, polling termination, error recovery, pagination boundary behavior, and regression are not captured by any REQ-Q-XXX. These behaviors are effectively untraceable.

**D8. spec.md:L320 and spec.md:L333 — Requirements contain implementation details (HOW)** — Severity: minor
REQ-Q-003 (spec.md:L320): "the system shall `/jobs/:jobId`로 이동하여 SPEC-UI-001 `CorrectionPanel`을 렌더링한다" — names a specific React component class (`CorrectionPanel`) and a specific URL route pattern. REQ-Q-006 (spec.md:L333): names specific HTTP method (`GET`), endpoint path (`/parse/jobs`), and query parameter names (`skip/limit/status/requires_correction`). These are implementation decisions embedded in requirements rather than behavioral outcomes.

---

## Chain-of-Verification Pass

Second-look findings: confirmed all first-pass findings. Additional checks performed:

- **REQ number sequencing end-to-end re-verified**: REQ-Q-001, 002, 003, 004, 005, 006, 007, 008 — full sequence, no gaps, no duplicates. MP-1 PASSES.
- **Every REQ-XXX traced to AC re-verified**: REQ-Q-001→AC-001, REQ-Q-002→AC-002, REQ-Q-003→AC-003, REQ-Q-004→AC-004, REQ-Q-005→AC-005, REQ-Q-006→AC-006, REQ-Q-007→AC-007, REQ-Q-008→AC-008. All 8 covered.
- **Exclusions section specificity verified**: spec.md:L47–L56 — 6 entries, all specific (파일 업로드/파싱 트리거 UI, 벌크 액션, 팀/멀티유저 큐 공유, 인증 화면, i18n, 트레이서빌리티/감사 로그). Substantive and specific. PASS.
- **Contradiction search**: spec.md:L258 (total ≤ 50 hide) vs REQ-Q-008 L340 (total > 50 show) — these are consistent, no contradiction. spec.md:L266 client-side sort vs spec.md:L210 backend created_at default — design choice, not contradiction.
- **Additional AC-007 ambiguity found**: acceptance.md:L47 says "신뢰도 오래된순(낮은순)" — the label "오래된순" (literally "oldest order") is a created_at sort label applied to confidence sorting. Using "오래된순/최신순" (oldest/newest) vocabulary for confidence values is semantically incorrect. Confidence should use "낮은순/높은순" (lowest/highest). This is an additional minor clarity defect.

**New defect from second pass:**

**D9. acceptance.md:L47 — AC-007 sort direction label semantically incorrect for confidence sort** — Severity: minor
"오래된순(낮은순)" applies date-ordering vocabulary ("오래된순" = oldest-first) to confidence values. While the parenthetical "(낮은순)" clarifies intent, the primary label is misleading. Confidence sorting should use "낮은순/높은순" (low-to-high/high-to-low), not "오래된순/최신순" (old-first/new-first). This ambiguity could cause a tester to misinterpret which direction is being tested.

---

## Regression Check

N/A — Iteration 1.

---

## Recommendation

This SPEC has three must-pass failures (MP-2 × 2 violations, MP-3 × 3 violations). All must be resolved before the SPEC can be approved.

**Fix 1 (MP-3, D1): Change `status` field value**
spec.md:L4 — Change `status: planned` to `status: draft`.

**Fix 2 (MP-3, D2): Rename `created` to `created_at`**
spec.md:L5 — Change `created: 2026-06-09` to `created_at: 2026-06-09`.

**Fix 3 (MP-3, D3): Add `labels` field**
spec.md after L6 — Add `labels: [ui, frontend, backend, queue, fullstack]` (or appropriate values).

Apply same 3 fixes to spec-compact.md:L1–L7 which has identical frontmatter defects.

**Fix 4 (MP-2, D4): Correct EARS keyword in REQ-Q-004**
spec.md:L325 — Change "**Where** `requires_correction`이 true이면" to "**While** `requires_correction`이 true이면". Update the section label at spec.md:L323 from "(State-Driven)" to "(State-Driven)" is already correct — only the keyword body needs correction.

**Fix 5 (MP-2, D5): Convert acceptance criteria to EARS format OR create a dedicated EARS AC section in spec.md**
Option A (preferred): Add a formal EARS Acceptance Criteria section to spec.md, converting each AC to EARS pattern. Keep acceptance.md as supplemental GWT test scenarios (not as the formal ACs).
Option B: Convert acceptance.md ACs to EARS format using State-driven / Event-driven patterns as appropriate for each scenario.

Example conversion for AC-001:
- Current: "Given…When 사용자가 `/jobs`로 이동하면 Then `JobQueueTable`이 렌더링된다"
- EARS: "When the user navigates to `/jobs`, the system shall render `JobQueueTable` with status, confidence, and created_at columns."

**Fix 6 (minor, D6): Correct EARS pattern for REQ-Q-008**
spec.md:L339 — Change from Event-driven "When 작업 수가 50개를 초과하면" to State-driven: "While 작업 총 수(total)가 50개를 초과하면, the system shall 페이지네이션 컨트롤(이전/다음, 현재 페이지 표시)을 표시한다."

**Fix 7 (minor, D7): Add REQ entries for orphaned edge-case behaviors**
acceptance.md:L57–L91 — Add REQ-Q-009 (empty state), REQ-Q-010 (null confidence display), REQ-Q-011 (invalid status 422), REQ-Q-012 (polling termination), REQ-Q-013 (error recovery) to spec.md §6, or explicitly acknowledge these are derived from existing REQs with sub-AC references.

**Fix 8 (minor, D9): Correct sort direction label in AC-007**
acceptance.md:L47 — Change "신뢰도 / 오래된순(낮은순)" to "신뢰도 / 낮은순" to use appropriate confidence-domain vocabulary.

---

Verdict: FAIL
