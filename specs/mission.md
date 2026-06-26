# ProjectMatchAI — Mission

> **Constitution Document · Version 1.0 · June 2026**
> This document is a living source of truth. Update it deliberately and with team consensus.

---

## 1. Project Vision

ProjectMatchAI is an AI-powered platform that connects students with mentors and real-world projects — not based solely on what a student already knows, but on who they have the potential to become.

We believe the right project at the right time, guided by the right mentor, is one of the most accelerating forces in a person's technical career. Our platform exists to make that match — intelligently, transparently, and at scale — for learners across both academic institutions and professional upskilling environments.

---

## 2. Problem Statement

### For Students

Students struggle to find meaningful projects that match their current skills while also stretching them toward new ones. Most matching systems are keyword-based and filter out candidates who lack exact-match experience — even if those candidates are highly capable of learning those skills within the project timeline.

### For Mentors

Mentors waste significant time reviewing unqualified candidates and lack structured tools to assess a student's growth potential beyond a list of technologies on a resume. There is no standardised feedback loop that makes the next match better than the last.

### For the Industry

There is a systemic gap between what universities and bootcamps teach and what real-world projects require. This gap is often not a matter of intelligence or effort — it is a matter of targeted, project-based exposure that students rarely get.

---

## 3. Goals

| #   | Goal                                                                                                                 |
| --- | -------------------------------------------------------------------------------------------------------------------- |
| G1  | Match students to projects based on **growth potential**, not just current skills                                    |
| G2  | Provide **explainable AI recommendations** — mentors always understand _why_ a candidate was ranked                  |
| G3  | Give students an **actionable learning roadmap** bridging the gap between their current profile and a target project |
| G4  | Enable mentors to make **faster, more confident decisions** through structured AI assistance                         |
| G5  | Collect and incorporate **mentor feedback** to continuously improve future recommendations                           |
| G6  | Generate career-supporting artefacts: **ATS reports** and **industry readiness reports** for students                |
| G7  | Support both **academic and professional** settings equally from day one                                             |
| G8  | Provide a **real-time collaboration channel** (chat) between matched students and mentors                            |

---

## 4. Non-Goals

| #   | Non-Goal                                                                                                 |
| --- | -------------------------------------------------------------------------------------------------------- |
| NG1 | We are **not** a job board or a freelance marketplace                                                    |
| NG2 | We are **not** an automated hiring system — the AI never makes the final decision                        |
| NG3 | We are **not** a learning management system (LMS) — we point students toward resources, not deliver them |
| NG4 | We are **not** a social network — profiles are functional, not performative                              |
| NG5 | We will **not** replace mentor judgment with algorithmic enforcement                                     |
| NG6 | We will **not** store or train on private student data without explicit consent                          |

---

## 5. Target Users

### Students

- University and college students (any stage, any discipline)
- Bootcamp graduates and self-taught developers seeking real-world experience
- Professionals looking to pivot or upskill through project-based learning
- Primary motivation: gaining experience, building a portfolio, learning under guidance

### Mentors

- Faculty members and professors assigning capstone or research projects
- Industry professionals volunteering or paid to guide learners
- Engineering leads seeking to assess early-career talent through project trials
- Primary motivation: finding capable, motivated, growth-oriented contributors

### Admins

- Platform operators responsible for user management, content moderation, and system health

---

## 6. Core Principles

### P1 — Humans Decide, AI Assists

The AI system produces ranked candidates with explanations. The mentor always makes the final acceptance decision. No automated matching without human review.

### P2 — Explainability Is Non-Negotiable

Every AI recommendation must be accompanied by a plain-language explanation. "Why was this student recommended?" must always have a clear, human-readable answer. Black-box scoring is unacceptable.

### P3 — Growth Over Credential

A student who can learn Python in three weeks for a project is more valuable than a student who listed Python on their resume two years ago and never used it since. The system is designed to surface potential, not just credentials.

### P4 — Feedback Closes the Loop

Mentor decisions and post-project feedback are first-class data. Every accept, reject, and project outcome is a signal that improves future recommendations. The system gets smarter with use.

### P5 — Privacy and Consent First

Student profiles, resumes, and embeddings are personal data. The system must be transparent about what is stored, how it is used, and how it can be deleted.

### P6 — Accessibility by Default

The platform must be usable by students and mentors regardless of their institution's resources, technical setup, or geography.

---

## 7. Guiding Engineering Principles

### E1 — Clean Architecture

Separate concerns strictly: API layer, service layer, repository layer. No business logic in route handlers. No database queries in service code that belongs in repositories.

### E2 — Feature-Based Structure

Both frontend and backend codebases are organised by feature/domain (e.g., `auth/`, `profile/`, `matching/`), not by technical layer. This enables AI-assisted development by making context local and self-contained.

### E3 — Modular AI Services

Each AI capability (embedding, reranking, LLM explanation, OCR, parsing) is encapsulated behind a well-defined service interface. AI providers can be swapped or upgraded without touching business logic.

### E4 — Configuration Over Code

All environment-specific values (API keys, model names, feature flags) live in environment variables. No hardcoded secrets or environment assumptions in source code.

### E5 — Test at Every Phase

Unit and integration tests are written as part of each phase's Definition of Done. A dedicated E2E/QA phase validates the integrated system before deployment.

### E6 — Incremental and Reviewable

Development proceeds in small, independently completable phases. Each phase produces a working, reviewable artefact. No phase depends on a subsequent phase being started.

### E7 — Observable Systems

Structured logging and error tracing are implemented from Phase 0. Every failure must be diagnosable from logs without attaching a debugger.

### E8 — Designed for AI-Assisted Development

Documentation, naming conventions, and code structure are written so that an AI coding agent can understand any module without needing context outside that module's directory.

---

## 8. AI Principles

### AI1 — Abstract Provider Interface

All LLM calls route through an abstract provider interface. Ollama (Qwen) and OpenAI are both supported and configured via environment variables. No model-specific logic leaks into business code.

### AI2 — Semantic Search First

Candidate retrieval uses pgvector semantic similarity search over dense embeddings (BAAI BGE). This captures conceptual alignment, not just keyword overlap.

### AI3 — Reranking for Precision

The initial semantic retrieval pool is reranked by a BGE Cross Encoder that scores each candidate against the full project description. Reranking improves precision beyond what embedding similarity alone can achieve.

### AI4 — Hybrid Scoring

Final candidate ranking combines semantic similarity, cross-encoder score, skill gap analysis, learning velocity estimation, and historical mentor feedback into a single transparent composite score.

### AI5 — LLM Explanations Are Grounded

LLM-generated match explanations are strictly grounded in the student's structured profile and the project's requirements. Hallucination is mitigated by providing structured context, not free-form prompting.

### AI6 — Resume Parsing Is Structured

PyMuPDF handles digital PDFs. PaddleOCR handles scanned documents. Parsed data is converted into a structured schema before embedding or display. Raw OCR output is never stored as the canonical profile.

### AI7 — Embeddings Are Versioned

Every embedding in the vector store records which model version and schema version produced it. If the embedding model changes, affected records are flagged for re-embedding.

---

## 9. Definition of Success

### MVP Success Criteria

| Criterion                                                                        | Target      |
| -------------------------------------------------------------------------------- | ----------- |
| A student can register, upload a resume, and have a structured profile generated | ✓ Working   |
| A mentor can create a project and receive a ranked list of student candidates    | ✓ Working   |
| Every candidate ranking includes a plain-language AI explanation                 | ✓ Present   |
| A matched student and mentor can communicate via real-time chat                  | ✓ Working   |
| Mentor feedback is captured and stored for future model improvement              | ✓ Stored    |
| Admin can manage users and moderate projects                                     | ✓ Working   |
| The platform functions for both academic and professional users                  | ✓ Validated |

### Long-Term Success Indicators

- Mentors report higher confidence in candidate selection compared to manual review
- Students report that recommended projects led to measurable skill growth
- Feedback loop demonstrably improves recommendation quality over cohort iterations
- Platform operates across at least two distinct institution types (university + industry program)

---

## 10. Future Vision

**Near Term (Post-MVP)**

- Skill gap learning roadmaps linked to curated external resources (YouTube, documentation, courses)
- Industry readiness scoring benchmarked against real job descriptions
- ATS report generation tailored to specific roles or companies

**Medium Term**

- Longitudinal student profiles that track skill development across multiple projects
- Mentor reputation and matching quality scores based on student outcomes
- Cohort-level analytics for institutions: which skills are most in demand, which gaps are most common

**Long Term**

- Multi-institution federated deployments with privacy-preserving profile sharing
- Fine-tuned domain-specific embedding models trained on platform feedback data
- Autonomous learning path generation: given a target role, generate the sequence of projects a student should pursue
- Open API for third-party institutions to integrate ProjectMatchAI recommendations into their own portals

---

_This document was authored as part of the ProjectMatchAI project constitution and should be reviewed and updated at each major version milestone._
