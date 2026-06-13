# SPEC-TEMPLATE-001 Tasks

## Milestone 0: Planning and Issue Setup

| ID | Task | Output | Status |
| --- | --- | --- | --- |
| T-000 | Create GitHub issue and update `issue_number` | Issue #29 recorded in `spec.md` | completed |
| T-001 | Confirm customer-runtime vs cloud-control-plane ownership | Architecture decision note | pending |
| T-002 | Validate FDA seed pack scope with RA SME | Seed pack review notes | pending |

## Milestone 1: Data Model and Fixtures

| ID | Task | Output | Status |
| --- | --- | --- | --- |
| T-010 | Add template schema models | `RegulatoryPathway`, `TemplatePack`, `TemplateDocument`, `TemplateSection`, `ApplicabilityRule`, `SourceReference` | pending |
| T-011 | Add checklist schema models | `Checklist`, `ChecklistItem` | pending |
| T-012 | Add pack validation utility | Fails regulatory sections without source refs | pending |
| T-013 | Add FDA 510(k) nIVD seed fixture | Versioned JSON/YAML pack | pending |
| T-014 | Add unit tests for applicability rules | Safe expression evaluation tests | pending |

## Milestone 2: API

| ID | Task | Output | Status |
| --- | --- | --- | --- |
| T-020 | Implement `GET /template-packs` | Pack listing API | pending |
| T-021 | Implement `POST /template-packs/resolve` | Product profile to pack resolution | pending |
| T-022 | Implement `POST /checklists/generate` | Checklist generation | pending |
| T-023 | Implement `GET /checklists/{id}` | Checklist detail API | pending |
| T-024 | Implement `PATCH /checklists/{id}/items/{item_id}` | Status update + audit | pending |

## Milestone 3: UI

| ID | Task | Output | Status |
| --- | --- | --- | --- |
| T-030 | Add product profile form | Initial pathway/profile input | pending |
| T-031 | Add template pack preview | Documents, sections, source refs | pending |
| T-032 | Add checklist view | Section status and blocking gaps | pending |
| T-033 | Add checklist item status controls | Draft/review/approve/not-applicable transitions | pending |

## Milestone 4: Export and Reconciliation

| ID | Task | Output | Status |
| --- | --- | --- | --- |
| T-040 | Export binder metadata JSON | Pack/checklist/source/audit export | pending |
| T-041 | Export checklist XLSX | Reviewer-friendly checklist | pending |
| T-042 | Add parser-to-template reconciliation hook | Uploaded doc fields mapped to template sections | pending |

## Milestone 5: Verification

| ID | Task | Output | Status |
| --- | --- | --- | --- |
| T-050 | Unit tests | Pack validation, applicability, checklist generation | pending |
| T-051 | API tests | Resolve/generate/detail/update endpoints | pending |
| T-052 | UI tests | Profile form, pack preview, checklist status changes | pending |
| T-053 | E2E smoke | Profile -> pack -> checklist -> status update -> export | pending |
| T-054 | Security checks | Tenant isolation and no arbitrary expression execution | pending |
