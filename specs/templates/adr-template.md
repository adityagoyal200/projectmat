# Architecture Decision Record (ADR) Template

> **Usage**: Copy this file to `specs/adrs/ADR-NNNN-<short-title>.md` where `NNNN` is a zero-padded sequence number (e.g., `ADR-0001-fastapi-over-django.md`). ADRs are immutable once accepted — if a decision changes, create a new ADR that supersedes the old one.

---

## ADR-NNNN — [Short Decision Title]

## Status

`[ ] Proposed` | `[ ] Accepted` | `[ ] Rejected` | `[ ] Deprecated` | `[ ] Superseded by ADR-XXXX`

## Date

<!-- YYYY-MM-DD when this ADR was written -->

## Authors

<!-- Name(s) of decision makers -->

## Deciders

<!-- Who must approve this decision before it is accepted -->

---

## Context

<!--
What is the situation, problem, or constraint that requires a decision?
Describe the forces at play: technical, business, team, timeline.
Be factual and neutral — do not advocate for the solution here.

Good context answers:
- What problem are we solving?
- Why does this need a decision now?
- What are the constraints (time, cost, team skill, hardware)?
-->

## Decision

<!--
Clearly state what was decided.
Start with: "We will use..." or "We will implement..."
One paragraph. If you cannot state it clearly in one paragraph, the decision is not clear enough.
-->

## Rationale

<!--
Why was this option chosen over the alternatives?
Connect each reason to a concrete constraint from the context above.
Avoid vague justifications like "it's simpler" — explain *why* it is simpler for *this team* on *this project*.
-->

**Primary reasons:**

1. **[Reason]** — [Explanation tied to a specific constraint]
2. **[Reason]** — [Explanation tied to a specific constraint]
3. **[Reason]** — [Explanation tied to a specific constraint]

---

## Alternatives Considered

<!--
List every meaningful alternative that was evaluated.
For each, explain why it was not chosen — be specific and fair.
-->

### Option A: [Name]

**Description**: [What this option entails]

## **Pros**:

- **Cons**:

-
- **Why rejected**: [Specific reason tied to project constraints]

  ***

### Option B: [Name]

**Description**: [What this option entails]

## **Pros**:

- **Cons**:

-
- **Why rejected**: [Specific reason tied to project constraints]

  ***

## Trade-offs Accepted

<!--
Every decision involves trade-offs. Be explicit about what you are giving up.
This section is the most honest part of an ADR.
-->

By choosing this approach, we accept:

- **[Trade-off]**: [Consequence and mitigation, if any]
- **[Trade-off]**: [Consequence and mitigation, if any]

---

## Consequences

<!--
What changes as a result of this decision?
List both positive and negative consequences.
Include any follow-up actions required.
-->

## **Positive**:

- **Negative**:

-
- **Follow-up actions**:

- [ ] [Action required as a result of this decision]
- [ ] [Action required as a result of this decision]

---

## Revisit Criteria

<!--
Under what conditions should this decision be revisited?
Be specific — this prevents endless rehashing of settled decisions.
-->

This decision should be revisited if:

- [Specific condition, e.g., "API rate limits exceed X requests/day"]
- [Specific condition, e.g., "Team grows beyond 5 engineers"]
- [Specific condition, e.g., "A specific metric falls below threshold"]

---

## References

<!--
Link to relevant documentation, benchmarks, discussions, or prior art.
-->

- [Link to relevant doc or discussion]
- [Link to benchmark or comparison]

---

_ADR Template version 1.0 — ProjectMatchAI_
