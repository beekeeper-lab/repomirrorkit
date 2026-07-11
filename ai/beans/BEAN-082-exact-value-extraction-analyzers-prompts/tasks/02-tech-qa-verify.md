# Task 02 — Tech-QA: independent verification

| Field | Value |
|-------|-------|
| **Owner** | tech-qa |
| **Depends On** | 01 |
| **Status** | Pending |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |

## Goal

Independently verify BEAN-082: error contracts + model rules extracted and
rendered on the python-flask fixture; contract matches BEAN-081 exactly;
chokepoint used for all literals; LLM parser strips code blocks; no verbatim
source-code leakage; suite + lint + mypy clean. Adversarial probes on
malformed source, contract shape drift, and code-block leakage.
