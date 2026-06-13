# Template-First RA Strategy Audit

Date: 2026-06-13
Scope: regulatory document generation, authoring, review, checklist, and submission-package workflow

## 1. Verdict

The user's hypothesis is correct.

The current product is mostly an ingestion-first review system: users upload existing IFU/SRS/RMS/test documents, the system parses them, surfaces low-confidence fields, runs cross-document guardrails, answers RAG questions, and exports audit evidence.

That is useful only after a team already has documents. For the target users in this repository, especially startups without mature RA/QA staff, the higher-value workflow starts earlier:

1. Select jurisdiction/pathway/device profile.
2. Generate a structured template pack and submission checklist.
3. Let the team author documents against that structure.
4. Ingest/version the authored documents.
5. Run gap, traceability, consistency, and evidence review.
6. Export review packages and audit history.

This is not a full product discard. It is a product-axis change. Parser, correction UI, review queue, RAG, guardrail, crawler, sync, and audit export remain useful, but they should move behind a template-first authoring and checklist layer.

## 2. Local Product Evidence

### 2.1 Current implementation center

Implemented API and UI surfaces found in the repo:

| Area | Existing surface | Meaning |
| --- | --- | --- |
| Upload | `POST /documents/upload` | Starts from an existing local file. |
| Parse jobs | `GET /parse/jobs`, `GET /parse/jobs/{job_id}` | Work queue is parse-job oriented. |
| Correction | `PATCH /parse/{job_id}/corrections`, `PATCH /documents/{doc_id}/fields` | Fixes extracted fields after parsing. |
| Guardrail | `POST /guardrail/run` | Checks consistency among existing document entities. |
| RAG | `POST /rag/query` | Answers against regulatory/customer knowledge. |
| Audit/export | `POST /audit/export`, `POST /audit/webhook` | Exports review/audit evidence. |
| Cloud crawler | `POST /crawl/trigger`, `GET /crawl/status/{job_id}` | Maintains external regulatory knowledge. |

This is a strong foundation for review, but it does not yet create the initial regulatory document structure.

### 2.2 Existing planning already hints at templates

The MRD already says the problem includes RA staff shortage and startup self-service, and explicitly references templates:

| File evidence | Finding |
| --- | --- |
| `docs/mrd.md:29` | Startup self-service pain is addressed by "templates, correction UI, role-based review queue". |
| `docs/mrd.md:53` | Consulting/testing partners need standard input templates and reusable checklists/reports. |
| `docs/mrd.md:64` | A startup CTO wants to complete basic upload/parse/review without a guide to build an initial document system. |
| `docs/mrd.md:65` | Partners want reusable standard input templates and review reports. |
| `docs/mrd.md:68` | X-ray/detector/PACS-specific document templates are a stated user story. |
| `docs/prd.md:13` | PRD says public regulatory knowledge plus customer documents should support standard document generation, consistency review, and impact analysis. |

But current SPECs are not template-first:

| SPEC | Center of gravity |
| --- | --- |
| `SPEC-API-001` | Runtime API, upload, parse, guardrail, RAG, audit. |
| `SPEC-PARSER-001` | DOCX/XLSX field extraction. |
| `SPEC-UI-001` | Parsed IFU correction panel. |
| `SPEC-UI-002` | Parse-job review queue. |
| `SPEC-CRAWLER-001` | FDA/MFDS/EU MDR knowledge collection. |

Conclusion: MRD contains the product intent, but PRD/SPEC execution drifted toward ingestion/review. A plan rebase is justified.

## 3. Official Regulatory Evidence

### 3.1 FDA eSTAR proves a structured template model

Source: FDA eSTAR Program
URL: https://www.fda.gov/medical-devices/how-study-and-market-your-device/estar-program
Observed on: 2026-06-13

Facts:

- FDA describes eSTAR as an interactive PDF form that guides applicants through preparing a comprehensive medical device submission.
- FDA says eSTAR provides a standardized, structured format for both reviewers and applicants.
- FDA lists mandatory use for medical device 510(k) and De Novo submissions unless exempted.
- FDA's current eSTAR page shows active template versions and version retirement dates.
- FDA notes that eSTAR displays only relevant sections based on applicant answers.
- eSTAR accepts attachments such as Word documents and Excel sheets, and FDA recommends clear attachment organization.

Product implication:

For US FDA 510(k)/De Novo, a template-first workflow is not just a UX idea. It mirrors the regulator's own submission model. The product should not simply parse arbitrary existing documents; it should guide teams through a pathway-specific structure and attach generated/authored evidence into that structure.

### 3.2 FDA software submission guidance proves document families must be structured

Source: FDA, Content of Premarket Submissions for Device Software Functions, June 2023
URL: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/content-premarket-submissions-device-software-functions
PDF: https://www.fda.gov/media/153781/download
Observed on: 2026-06-13

Facts:

- FDA says the guidance concerns recommended documentation for evaluating safety and effectiveness of device software functions.
- The table of contents names document groups such as software description, risk management file, SRS, architecture diagram, software design specification, development/configuration/maintenance practices, verification and validation testing, version history, and unresolved anomalies.
- FDA guidance connects user needs, requirements, design, testing, and implemented risk controls as traceability.
- The guidance references software documentation generated during development, verification, and validation.

Product implication:

For software-enabled devices, "review after upload" is late. SRS, risk controls, architecture, V&V, version history, anomalies, and traceability should be authored and maintained as structured artifacts from the start.

### 3.3 EU MDR requires organized technical documentation and PMS documentation

Source: EUR-Lex, Regulation (EU) 2017/745 on medical devices
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32017R0745
Observed on: 2026-06-13

Facts:

- MDR Annex II defines technical documentation content, including device description, information supplied by the manufacturer, design/manufacturing information, GSPR conformity information, benefit-risk/risk management, and product verification/validation.
- MDR Annex III says post-market surveillance technical documentation must be clear, organized, searchable, and unambiguous.
- MDR Annex I includes label and IFU requirements and residual-risk communication.

Product implication:

For EU MDR, the system should generate and maintain an Annex II/III/GSPR-oriented technical documentation workspace and checklist. Upload parsing alone cannot guarantee completeness, searchability, or traceability.

### 3.4 MFDS source coverage exists but template extraction is not yet modeled

Source: MFDS guide/guideline listing
URL: https://www.mfds.go.kr/brd/m_218/list.do
Observed on: 2026-06-13

Facts:

- MFDS has an official guide/guideline board under law/materials.
- The listing supports category filtering including medical devices.
- The repository already points the crawler default at this MFDS listing.

Product implication:

MFDS should be a first-class knowledge source, but a Korean submission template pack should not be hardcoded until official MFDS guidance/forms are harvested, versioned, and mapped by document type. Build the template registry so MFDS packs can be added without changing the workflow engine.

## 4. User-Value Assessment

### 4.1 Current user benefit

The implemented system benefits users who already have documents:

- Reduces manual reading of long IFU/SRS/RMS/test files.
- Finds low-confidence extracted fields and forces correction.
- Gives a review queue so RA/QA can prioritize work.
- Creates an audit trail for review/correction/export.
- Lets users ask regulatory questions against curated knowledge.
- Supports local processing for sensitive customer documents.

This is real value, but it is reactive.

### 4.2 Current user gap

For an early medical-device startup, the hardest first question is often not "is my completed IFU consistent?" It is:

- What documents do I need for this device and market?
- Which sections must each document contain?
- Which evidence belongs in each section?
- Which requirements, risks, tests, labels, and IFU warnings need links?
- What is missing before I request RA review?

The current product answers these only indirectly. It asks users to bring documents first.

### 4.3 Template-first user benefit

A template-first product gives users:

- A concrete starting structure instead of a blank page.
- Pathway-specific completeness checklists.
- Earlier capture of evidence during development, not after development.
- Built-in traceability from user need -> requirement -> risk control -> test -> IFU/labeling.
- Faster RA review because missing sections are explicit before review starts.
- Better consultant/partner handoff because inputs are standardized.
- Lower rework because the parser reviews documents created from known structure.

This directly matches the MRD's self-service and startup pain points.

## 5. Revised Product Model

### 5.1 New workflow

1. Product profile
   - Device type, intended use, user group, software involvement, markets, risk class, standards claims, predicate/clinical strategy.

2. Pathway selection
   - US FDA 510(k)/De Novo/PMA/Q-Sub.
   - EU MDR CE technical documentation.
   - MFDS approval/certification/notification pack, after official mapping.

3. Template pack generation
   - Document list.
   - Required sections.
   - Section-level instructions.
   - Evidence placeholders.
   - Source citations.
   - Versioned regulatory basis.

4. Guided authoring
   - Users write in structured sections, not arbitrary files.
   - AI may draft section starters, but every claim must remain editable and reviewable.

5. Evidence binder
   - Attach tests, risk files, diagrams, clinical/performance evidence, cybersecurity artifacts, usability files, labels, IFU drafts.

6. Checklist and gap analysis
   - Completeness.
   - Source-backed requirement coverage.
   - Missing evidence.
   - Inconsistent terminology.
   - Unlinked risk controls/tests/warnings.

7. Review workspace
   - RA/QA review queue.
   - Findings.
   - Assignments.
   - Approval/rejection.
   - Audit trail.

8. Export
   - DOCX/XLSX/PDF/JSON package.
   - eSTAR-compatible attachment binder first; direct eSTAR PDF automation only after feasibility validation.
   - EU MDR Annex II/III technical file package.

### 5.2 Keep vs change

Keep:

- Parser engine.
- Manual correction UI.
- Review queue.
- RAG.
- Guardrail.
- Crawler/sync.
- Audit export.
- Local runtime security model.

Add before them:

- Regulatory pathway classifier.
- Template pack registry.
- Structured authoring workspace.
- Checklist/gap engine.
- Requirement-to-evidence matrix.
- Evidence binder.
- Template-aware export.

Reframe:

- Parser becomes import/reconciliation, not the primary starting point.
- RAG becomes source-backed authoring assistance, not just Q&A.
- Guardrail becomes continuous during authoring, not only after upload.
- Audit records authoring/review lifecycle, not only correction events.

## 6. Proposed New SPEC Set

### SPEC-TEMPLATE-001: Regulatory Pathway and Template Pack Registry

Purpose:

- Store versioned template packs by jurisdiction, pathway, device family, and document type.
- Each template section must carry source references and applicability rules.

Core entities:

- `RegulatoryPathway`
- `TemplatePack`
- `TemplateDocument`
- `TemplateSection`
- `ApplicabilityRule`
- `SourceReference`

Acceptance:

- Given a product profile, the system returns the applicable template pack and document checklist.
- Every generated section has a source reference or is explicitly marked as company policy/internal best practice.

### SPEC-AUTHORING-001: Guided Regulatory Authoring Workspace

Purpose:

- Let users draft and maintain IFU/SRS/RMS/software/evidence sections inside the system.

Acceptance:

- Users can create a document from a template.
- Users can edit section content, attach evidence, and track status by section.
- AI-generated text is labeled as draft and requires human approval.

### SPEC-CHECKLIST-001: Submission Checklist and Gap Engine

Purpose:

- Convert template sections and pathway rules into a live checklist.

Acceptance:

- The checklist distinguishes not started, drafted, evidence attached, reviewed, approved, not applicable, and blocked.
- Missing required sections and missing evidence create findings.

### SPEC-EVIDENCE-001: Traceability and Evidence Binder

Purpose:

- Link user needs, requirements, risk controls, tests, labels, IFU warnings, and source files.

Acceptance:

- The system surfaces unlinked high-risk controls, unverified requirements, and IFU warnings without corresponding risk controls.

### SPEC-EXPORT-001: Template-Aware Package Export

Purpose:

- Export authored/reviewed artifacts by pathway.

Acceptance:

- US FDA MVP exports an eSTAR attachment binder and metadata checklist.
- EU MDR MVP exports Annex II/III technical documentation sections and GSPR checklist.
- Exports include source references, version, approver, and audit hashes.

## 7. Priority Recommendation

### P0: Rebase the roadmap, not the codebase

Do first:

- Create `SPEC-TEMPLATE-001`.
- Create a minimal template registry schema.
- Add one pathway MVP: US FDA 510(k) nIVD/eSTAR attachment-binder style.
- Add product profile -> template pack selection.
- Add checklist generation.

Why:

- FDA eSTAR is the strongest official proof and closest to a structured template model.
- It avoids overbuilding every jurisdiction at once.
- It turns current parser/review work into a meaningful downstream validation stage.

### P1: Add authoring workspace

- Section editor.
- Evidence attachment.
- AI-assisted draft generation with source references.
- Human approval state.
- Import existing DOCX/XLSX into a template section.

### P2: Add EU MDR Annex II/III/GSPR pack

- MDR technical documentation structure.
- GSPR checklist.
- PMS/PMCF placeholders and gap rules.

### P3: Add MFDS pack

- Harvest and version official MFDS forms/guidelines.
- Map Korean document families and forms.
- Require RA SME review before marking pack production-ready.

## 8. Risk Controls

| Risk | Control |
| --- | --- |
| AI generates legally unsafe completed submissions | Treat AI text as draft only; require human RA/QA approval. |
| Official templates change | Version template packs and source references; crawler creates update alerts. |
| Standards are copyrighted | Store mappings and placeholders; do not embed proprietary standard text unless licensed. |
| Jurisdiction branching explodes | Start with one device family and one pathway; add packs through registry metadata. |
| eSTAR dynamic PDF automation is brittle | First export binder/checklist; validate XML/PDF automation separately. |
| Regulatory advice liability | Present as structured authoring/review support, not final legal/regulatory determination. |

## 9. Final Decision

Plan overhaul is necessary.

Not because the current implementation is wrong, but because it solves the second half of the user journey. The higher-value product begins before documents exist. The platform should become:

Template pack -> guided authoring -> checklist/gap analysis -> ingestion/reconciliation -> AI review/guardrail -> audit/export.

This aligns better with:

- Existing MRD template and self-service user stories.
- FDA eSTAR's structured submission model.
- FDA software documentation expectations.
- EU MDR technical documentation structure.
- Current crawler/RAG/guardrail architecture.

The next concrete action should be to open a new roadmap/spec issue for `SPEC-TEMPLATE-001` and freeze additional parser-only expansion until the template registry and checklist engine are defined.
