# BEAN-092: Feature Clustering for Action-Named Routes (Blueprint / Module Affinity)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-092 |
| **Status** | Unapproved |
| **Priority** | Medium |
| **Created** | 2026-11-11 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Path-based resource keys cluster `/follow/<u>`, `/explore`, `/index`, `/export_posts` as separate one-route features (microblog: 20 features, many of size 1-3). Blueprint/module membership and shared models are better affinity signals for action-named routes.

## Goal

Add blueprint/module (and shared-model/form) affinity to `features.py` clustering when path keys do not match a model; keep determinism and the manifest schema.

## Acceptance Criteria

- [ ] Microblog yields <=10 features with sensible names (auth, main, api, messaging...)
- [ ] Clustering remains byte-deterministic
- [ ] Existing fixture feature tests unchanged
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: real-world triage of the microblog app (`docs/real-world-triage-microblog.md`), 2026-11-11.
