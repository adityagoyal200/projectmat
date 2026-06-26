# ProjectMatchAI — Engineering Principles

> **Constitution Document · Version 1.0 · June 2026**
> This document defines **how** we build ProjectMatchAI. Where `mission.md` answers "What are we building?", this document answers "How do we build it?". Every engineering decision, feature design, and code review should be measured against these principles.

---

## Why This Document Exists

Principles prevent two failure modes:

1. **Over-engineering**: Building systems for problems that do not yet exist
2. **Under-engineering**: Cutting corners that create unrecoverable technical debt

These principles are not aspirational. They are operational constraints. When in doubt, a principle wins over an individual opinion.

---

## Core Principles

---

### 1. YAGNI — You Aren't Gonna Need It

> Build only what is needed for the current phase. Do not build for imagined future requirements.

**In practice**

- If a feature is not in the current phase's Definition of Done, do not implement it
- If a design decision adds complexity to support a future use case that doesn't exist yet, reject it
- Post-MVP features belong in the backlog, not the codebase

**Anti-patterns to avoid**

- Adding optional fields "just in case"
- Abstracting before there are two concrete use cases
- Building configuration options for settings no one has requested

---

### 2. KISS — Keep It Simple, Stupid

> The simplest solution that satisfies the requirements is the correct solution.

**In practice**

- Choose boring technology over novel technology when both solve the problem equally well
- A function that does one thing is better than a function that does one thing with twelve options
- If you need to explain why a design is clever, it is not simple enough

**Applied to this project**

- Vite + React over Next.js — all routes are authenticated; SSR adds complexity with no benefit
- FastAPI over Django — the AI layer is Python-native; the admin is deferred
- `ai/generation/` as a single module over distributed LLM calls in every service

---

### 3. Feature First

> Ship a working feature before optimising it. Optimise only what is proven to be slow.

**In practice**

- The MVP exists to validate one hypothesis: "Can AI match students to projects better than manual review?"
- Every engineering hour spent on infrastructure, tooling, or non-core features before the hypothesis is tested is waste
- Performance optimisation, caching, and scaling belong in Phase C, not Phase 0

**Corollary**
If the AI matching quality is poor, no amount of polished UI or fast response times will save the product.

---

### 4. AI Agnostic

> No business logic should depend on a specific AI provider, model, or API.

**In practice**

- All LLM calls go through `LLMProvider` — an abstract interface with `GroqProvider` and `OllamaProvider` implementations
- All embedding calls go through `EmbeddingService`
- All text generation (explanations, roadmaps, reports) goes through `ai/generation/`
- Swapping from Groq to OpenAI to Ollama requires changing one environment variable, not the codebase

**Why this matters**

- The AI landscape changes rapidly. A model that is state-of-the-art today may be obsolete or prohibitively expensive in six months
- Vendor lock-in at the model level is a strategic risk for an AI-first product

---

### 5. SOLID

Brief application to this codebase:

| Principle                 | Application                                                                                                                                                                 |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Single Responsibility** | `router.py` routes only; `service.py` contains business logic only; `repository.py` queries only                                                                            |
| **Open/Closed**           | `LLMProvider` and `EmbeddingService` are open for extension (new providers) without modifying existing code                                                                 |
| **Liskov Substitution**   | `GroqProvider` and `OllamaProvider` are interchangeable — any code that accepts `LLMProvider` works with both                                                               |
| **Interface Segregation** | Don't force a `GenerationService` to implement `EmbeddingService` methods — keep interfaces narrow                                                                          |
| **Dependency Inversion**  | Services depend on abstract interfaces (`LLMProvider`, `EmbeddingService`), not concrete implementations. FastAPI `Depends()` injects the correct concrete class at runtime |

---

### 6. Modularity

> Every feature is a self-contained module. Modules communicate through explicit interfaces, not by reaching into each other's internals.

**Structure rules**

- A feature module owns its router, service, repository, schemas, and models
- Cross-feature communication goes through service method calls or database queries — never by importing another feature's internal functions
- The `ai/` directory is a shared library, not a feature module. It has no knowledge of application features

**Folder law**: If you cannot delete a feature folder without breaking another feature folder, the boundaries are wrong.

---

### 7. Testing First

> A feature is not done until its tests are written and passing.

**In practice**

- Tests are part of every phase's Definition of Done — not an afterthought
- Write tests alongside code, not after the feature is "working"
- A test that covers real behaviour (integration test) is worth more than a test that mocks everything (pure unit test on trivial logic)
- AI pipeline components (scoring, metrics) must have unit tests with hardcoded expected values — not just "it runs without crashing"

**Test confidence pyramid for this project**

```
         [E2E — Playwright]         ← Slowest, highest confidence, fewest
       [Integration — httpx]        ← Core: every endpoint tested
    [Unit — pytest / Vitest]        ← Fast: pure functions, scoring, parsing
[AI Evaluation — metrics runner]    ← Offline: Precision@K, NDCG, MRR
```

---

### 8. Documentation First

> Code without documentation is a liability, not an asset.

**In practice**

- Every API endpoint is self-documented via FastAPI's OpenAPI auto-generation
- Every new feature follows `specs/templates/feature-template.md` before implementation begins
- Every architecture decision that involves a trade-off is recorded in an ADR using `specs/templates/adr-template.md`
- Docstrings are required on all public functions and classes (Google-style)
- The `specs/` directory is the source of truth. If the spec and the code disagree, the spec is wrong — update it

**AI agent corollary**: AI coding agents derive context from documentation. Undocumented code produces incorrect AI-generated continuations.

---

### 9. No Premature Optimisation

> "Premature optimisation is the root of all evil." — Knuth

**In practice**

- Do not add caching before measuring that a query is slow
- Do not add a task queue before measuring that a synchronous call is blocking
- Do not add horizontal scaling infrastructure before measuring that a single instance is saturated
- Use `EXPLAIN ANALYZE` before adding a database index

**When optimisation is appropriate**

- A measured latency exceeds a defined SLA (e.g., candidate retrieval > 500ms)
- A profiling tool (py-spy, clinic.js) identifies a specific hot path
- A load test demonstrates that the current architecture cannot handle expected peak load

---

### 10. Explicit Over Implicit

> Code should do exactly what it says it does, with no hidden behaviour.

**In practice**

- FastAPI `Depends()` makes all dependencies explicit in function signatures
- Environment variables are centralised in `app/config.py` — no `os.getenv()` scattered through the codebase
- Pydantic schemas define exact request and response shapes — no untyped dictionaries passed between layers
- Provider selection (`LLM_PROVIDER=groq`) is explicit in configuration, not hardcoded conditionals

---

## Principle Application Guide

When making any engineering decision, apply this checklist:

```
[ ] Does it already exist? (check before building — YAGNI)
[ ] Is this the simplest solution? (KISS)
[ ] Does this depend on a specific AI vendor? (AI Agnostic)
[ ] Are responsibilities separated cleanly? (SOLID, Modularity)
[ ] Is it documented before implementation starts? (Documentation First)
[ ] Will it be tested as part of this phase? (Testing First)
[ ] Is there evidence that optimisation is needed? (No Premature Optimisation)
```

---

_This document was authored as part of the ProjectMatchAI engineering constitution. It should be reviewed and updated when the team grows or the project enters a fundamentally new phase (e.g., multi-tenant, open API)._
