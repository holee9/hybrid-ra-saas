---
id: SPEC-TEMPLATE-001
version: 0.1.0
status: draft
created_at: 2026-06-13
updated: 2026-06-13
author: codex
priority: critical
issue_number: 29
labels: ["spec", "regulatory", "templates", "checklist", "authoring"]
---

# SPEC-TEMPLATE-001: Regulatory Template Pack Registry

## History

- 2026-06-13 (v0.1.0): Template-first strategy audit 결과를 반영한 초안 작성. 기존 ingestion-first 흐름을 유지하되, 제품 시작점을 pathway-specific template pack과 checklist로 재정렬한다.

## 0. Scope

### 0.1 Purpose

The system shall provide a versioned regulatory template pack registry that maps a product profile to the documents, sections, evidence placeholders, source references, and checklist items needed for a regulatory pathway.

This SPEC intentionally does not replace the parser, correction UI, review queue, RAG, guardrail, crawler, or audit export. It makes those modules downstream consumers of a structured authoring/checklist model.

### 0.2 In Scope

- Product profile input model for pathway selection.
- Regulatory pathway metadata.
- Template pack registry.
- Template document and section definitions.
- Section applicability rules.
- Source references for every regulatory-derived section.
- Checklist generation from template sections.
- Initial seed pack for US FDA 510(k) nIVD/eSTAR-style attachment binder.
- API contract for listing packs, resolving a pack, and generating a checklist.

### 0.3 Out of Scope

- Full guided authoring editor. This belongs in `SPEC-AUTHORING-001`.
- eSTAR dynamic PDF editing/import automation. This needs a separate feasibility spike.
- EU MDR Annex II/III implementation. This is planned for a follow-up pack after registry MVP.
- MFDS production-ready pack. The official MFDS source map must be harvested and reviewed first.
- Automatic final regulatory decision or legal/regulatory sign-off.

## 1. Background

The current product starts with existing customer documents:

- Upload document.
- Parse fields.
- Correct low-confidence fields.
- Run guardrail and RAG review.
- Export audit evidence.

This is useful after documents exist, but MRD user stories already mention standard templates, self-service startup onboarding, reusable checklists, and X-ray/PACS-specific document templates. Official regulatory evidence also supports a structured-template approach:

- FDA eSTAR is a standardized, structured interactive submission template for many 510(k)/De Novo submissions.
- FDA software guidance organizes expected documentation into named artifacts such as software description, risk management file, SRS, architecture, SDS, V&V testing, version history, anomalies, and traceability.
- EU MDR Annex II/III requires organized technical and post-market surveillance documentation.

Therefore the product should start from template packs, not from arbitrary uploaded files only.

## 2. User Outcomes

- A startup user can select a device profile and market, then receive a concrete document checklist instead of a blank page.
- RA/QA reviewers can see which sections are missing, drafted, evidence-backed, reviewed, approved, or not applicable.
- Consultants can reuse the same structured input model across customers.
- Existing parser and review tools can reconcile uploaded files against known template sections.
- Regulatory knowledge updates can be mapped to affected template packs and checklist items.

## 3. Data Model

### 3.1 ProductProfile

Fields:

- `profile_id`
- `tenant_id`
- `device_name`
- `device_family`
- `intended_use`
- `target_markets`
- `software_in_device`
- `risk_class`
- `sterile`
- `measuring_function`
- `uses_ai_ml`
- `contains_cybersecurity_surface`
- `predicate_strategy`
- `standards_claims`

### 3.2 RegulatoryPathway

Fields:

- `pathway_id`
- `jurisdiction`
- `authority`
- `pathway_type`
- `version`
- `effective_from`
- `effective_to`
- `status`

Examples:

- `US-FDA-510K-NIVD`
- `US-FDA-DE_NOVO-NIVD`
- `EU-MDR-ANNEX-II-III`
- `KR-MFDS-MEDICAL_DEVICE`

### 3.3 TemplatePack

Fields:

- `pack_id`
- `pathway_id`
- `device_family`
- `name`
- `version`
- `status`
- `source_version`
- `created_at`
- `updated_at`

### 3.4 TemplateDocument

Fields:

- `document_id`
- `pack_id`
- `doc_type`
- `title`
- `required`
- `sort_order`
- `export_format`

Initial doc types:

- `ADMIN`
- `DEVICE_DESCRIPTION`
- `INDICATIONS_FOR_USE`
- `LABELING_IFU`
- `SOFTWARE_DESCRIPTION`
- `SOFTWARE_REQUIREMENTS`
- `RISK_MANAGEMENT`
- `ARCHITECTURE`
- `VERIFICATION_VALIDATION`
- `CYBERSECURITY`
- `HUMAN_FACTORS`
- `PERFORMANCE_TESTING`
- `TRACEABILITY_MATRIX`
- `AUDIT_SUMMARY`

### 3.5 TemplateSection

Fields:

- `section_id`
- `document_id`
- `section_key`
- `title`
- `required`
- `instructions`
- `placeholder`
- `applicability_rule_id`
- `source_reference_ids`
- `sort_order`

### 3.6 ApplicabilityRule

Fields:

- `rule_id`
- `expression`
- `explanation`

Examples:

- `software_in_device == true`
- `contains_cybersecurity_surface == true`
- `sterile == true`
- `target_markets contains "US-FDA"`

### 3.7 SourceReference

Fields:

- `source_id`
- `authority`
- `title`
- `url`
- `retrieved_at`
- `version_label`
- `section_ref`
- `notes`

Every regulatory-derived template section must have at least one `SourceReference`. Internal best-practice sections must be explicitly marked as internal and must not be presented as regulatory requirements.

### 3.8 ChecklistItem

Fields:

- `checklist_item_id`
- `profile_id`
- `pack_id`
- `document_id`
- `section_id`
- `status`
- `required`
- `blocking`
- `evidence_required`
- `reviewer_status`

Allowed statuses:

- `not_started`
- `drafted`
- `evidence_attached`
- `needs_review`
- `approved`
- `not_applicable`
- `blocked`

## 4. API Contract

### 4.1 `GET /template-packs`

Returns available template packs filtered by jurisdiction, pathway, device family, and status.

Query:

- `jurisdiction`
- `pathway_type`
- `device_family`
- `status`

### 4.2 `POST /template-packs/resolve`

Given a `ProductProfile`, returns the best matching `TemplatePack` and the evaluated applicability map.

Request:

- `product_profile`

Response:

- `pack`
- `matched_pathway`
- `applicable_documents`
- `applicable_sections`
- `excluded_sections`
- `source_references`

### 4.3 `POST /checklists/generate`

Given a `ProductProfile` and `pack_id`, creates checklist items for all applicable documents and sections.

Request:

- `profile_id`
- `pack_id`

Response:

- `checklist_id`
- `items`
- `required_count`
- `blocking_count`

### 4.4 `GET /checklists/{checklist_id}`

Returns checklist status, item details, source references, and evidence attachment state.

### 4.5 `PATCH /checklists/{checklist_id}/items/{item_id}`

Updates checklist status or reviewer status. All updates must create audit events.

## 5. MVP Seed Pack

### 5.1 US FDA 510(k) nIVD/eSTAR-style attachment binder

The first seed pack should not attempt to edit the dynamic eSTAR PDF. It should generate:

- Product profile checklist.
- eSTAR-oriented attachment binder structure.
- Document/section checklist.
- Evidence placeholders.
- Source references.
- Exportable JSON/DOCX/XLSX binder metadata.

Initial source references:

- FDA eSTAR Program: https://www.fda.gov/medical-devices/how-study-and-market-your-device/estar-program
- FDA software submission guidance: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/content-premarket-submissions-device-software-functions
- FDA software guidance PDF: https://www.fda.gov/media/153781/download

## 6. Requirements

- REQ-TEMPLATE-001: WHEN a user provides a product profile, THE SYSTEM SHALL resolve the most applicable regulatory template pack for the selected jurisdiction and pathway.
- REQ-TEMPLATE-002: WHEN a template section is derived from a regulatory source, THE SYSTEM SHALL attach at least one source reference to that section.
- REQ-TEMPLATE-003: WHEN an applicability rule evaluates false, THE SYSTEM SHALL exclude the section from the active checklist and record the reason.
- REQ-TEMPLATE-004: WHEN a checklist is generated, THE SYSTEM SHALL create one checklist item per applicable required or optional section.
- REQ-TEMPLATE-005: WHEN a checklist item changes status, THE SYSTEM SHALL record an audit event with before/after state.
- REQ-TEMPLATE-006: WHEN a template pack source changes version, THE SYSTEM SHALL allow old checklists to retain their original source version and new checklists to use the updated version.
- REQ-TEMPLATE-007: WHEN a section is internal best practice rather than a regulatory requirement, THE SYSTEM SHALL label it as internal and SHALL NOT present it as an authority-mandated requirement.
- REQ-TEMPLATE-008: WHEN exporting binder metadata, THE SYSTEM SHALL include pack version, source references, checklist statuses, reviewer states, and audit hashes.
- REQ-TEMPLATE-009: WHEN a user imports an existing DOCX/XLSX document, downstream parser/reconciliation SHALL be able to map extracted fields to template sections where possible.
- REQ-TEMPLATE-010: WHEN no matching template pack exists, THE SYSTEM SHALL return a clear unsupported-pathway response and SHALL NOT fabricate a regulatory template.

## 7. Acceptance Criteria

- AC-001: Given a US FDA 510(k) nIVD product profile, when the resolve endpoint is called, the system returns the FDA 510(k) seed pack and applicable section list.
- AC-002: Given `software_in_device=false`, when checklist generation runs, software-only sections are excluded with an applicability reason.
- AC-003: Given `software_in_device=true`, when checklist generation runs, software description, SRS, architecture, V&V, version history, and traceability sections are included.
- AC-004: Given a regulatory-derived section without source references, validation fails.
- AC-005: Given a checklist item status update, an audit event is recorded.
- AC-006: Given a template pack version update, an existing checklist still references the original pack version.
- AC-007: Given an unsupported jurisdiction/pathway, the system returns an unsupported response instead of generating speculative content.
- AC-008: Given an export request, binder metadata includes checklist status, source references, pack version, and audit hashes.

## 8. Implementation Notes

- Seed data should be stored as structured JSON/YAML fixtures before adding a database admin UI.
- Applicability expressions should start as a small safe expression language, not arbitrary code execution.
- The first UI can be a read-only checklist view plus status update controls; full authoring is separate.
- Template validation should run in CI so packs cannot be committed without source references.
- The crawler should eventually notify when source URLs or versions change, but source update handling is not required for the first MVP.

## 9. Open Decisions

- Whether to implement template packs in the customer runtime only, cloud control plane only, or both with sync.
- Whether seed packs should live as migration data, static files, or cloud-delivered knowledge packs.
- Whether eSTAR XML data import/export is technically reliable enough for a later direct integration.
- Which first device family to support beyond the generic nIVD medical device profile.
