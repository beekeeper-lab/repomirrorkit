# RepoMirrorKit — Code Review & Improvement Backlog

**Reviewed:** 2026-05-01
**Reviewer:** Claude Code
**Scope:** ~20.6k LOC Python (`src/`), ~50 unit tests (`tests/`), docs, packaging

---

## TL;DR

The project's stated goal is **"given a Git repo, produce a list of requirements sufficient to recreate the project."** The codebase is well-architected as a pipeline (Stage A clone → B inventory/detect → C 14 surface analyzers → C2 LLM enrichment → D traceability → E beans → F coverage → G project-folder generation) and the engineering quality is generally solid. However, **the output does not yet deliver the goal**: it produces structural analysis artifacts (per-surface "beans") and a Claude Code project scaffold, not a single, behavioral, recreation-ready specification. Several other items below are stale or vestigial.

There is no single artifact a user can hand to another developer (or to Claude) and say "build this from scratch."

---

## Goal alignment — does this deliver "requirements to recreate the project"?

**Mostly no, by default.** With LLM enrichment off (the default — see `cli.py:115` `llm_enabled` defaults to `False`), beans contain structural facts plus literal `"TODO: Describe the expected behavior..."` placeholders.

### Findings

- **Beans without LLM enrichment are placeholders.** `harvester/beans/templates.py:113-118` writes `"TODO: Describe the expected behavior from a user/system perspective."` whenever `enrichment.behavioral_description` is absent. Same pattern at lines 138-139 (Given/When/Then), 147-148 (Data flow). Without `--llm-enabled`, the output is a structural index, not requirements.
- **No canonical "rebuild this" artifact.** Stage E writes one file per surface (potentially hundreds of beans) into `<out>/beans/`. Stage G writes a Claude Code project scaffold (`project-folder/CLAUDE.md`, agents, stack convention files) describing the *team* and *tech stack*. There is no top-level `REQUIREMENTS.md` (or equivalent) consolidating "what does this project do, and what would you need to build to recreate it."
- **Stage G generates a workflow scaffold, not a spec.** `harvester/generator/assembler.py:91-141` copies the *current* project's `.claude/` directory wholesale into `<out>/project-folder/.claude/` and produces a CLAUDE.md describing detected stacks + a persona roster. This is useful for *running* a Claude Code project, but it doesn't say "here are the routes, models, behaviors and acceptance criteria to implement."
- **Behavior is shallow.** Analyzers extract structure (routes, models, components, deps). They do not extract *user-facing intent*: what each route does for the user, what business rules a model enforces, what the success/failure flows are. Without the LLM, intent is missing entirely. With the LLM, it's per-surface but never aggregated.
- **Output is fragmented.** Per-surface beans + per-stage reports + per-stack convention files = dozens to hundreds of files with no single "front door." A consumer (human or LLM) has to crawl them all.

### Improvement ideas (concrete, ordered roughly by impact)

1. **Generate a single `REQUIREMENTS.md` at the top level of the output.** Sections per domain (Routes/Pages, APIs, Data Models, Auth, Background Jobs, Integrations, Build & Deploy). Each section summarizes count + lists named items with one-line descriptions; deep-link to the bean for detail. This is the artifact a user hands to someone saying "build this."
2. **Promote LLM enrichment from optional to default-on (with a `--no-llm` opt-out).** Without it, the tool can't deliver on "requirements." If no API key is present, fail fast with a helpful error explaining the trade-off, or emit a clearly-labeled "structural inventory" mode.
3. **Add a behavioral-spec analyzer.** New `analyzers/behavioral_spec.py` that mines docstrings, commit messages near a surface, and *test names/assertions* (e.g., `test_user_can_log_in_with_valid_credentials`) to infer intent without an LLM call. This is cheap signal that's currently ignored.
4. **Generate a Gherkin `.feature` file per major surface.** Routes/APIs naturally translate to `Feature/Scenario/Given/When/Then`. The bean template already pretends to do this (`templates.py:128-140`); take the next step and emit canonical `.feature` files Cucumber-style. They're machine-readable AND human-readable.
5. **Generate `.env.example` from config surfaces.** The `analyze_config` analyzer already finds env-var reads. Aggregate them into a generated `.env.example` listing each var, where it's read, and (if LLM-enabled) what it's for. This is a major recreate-the-project artifact missing today.
6. **Generate a data-model relationship report.** `analyzers/models.py` (951 LOC) extracts models. Add a relationships pass: foreign keys, cardinalities, cascade rules → `<out>/data-model.md` and optionally a Mermaid ER diagram embedded in `REQUIREMENTS.md`. Today's output cannot rebuild the schema.
7. **Generate a runnable-commands inventory.** `analyzers/build_deploy.py` already finds CI/scripts. Promote this to a top-level `RUNBOOK.md` that lists: how to install, how to run dev, how to test, how to build, how to deploy — derived directly from package.json scripts, Makefile, Dockerfile, CI YAML.
8. **Re-frame Stage G's purpose.** Either:
   - (a) Drop it as a separate stage and fold its outputs (`CLAUDE.md`, `.claude/`) into the recreate-the-project bundle, or
   - (b) Make it explicitly the "starter kit for working on a recreated version" stage and document that. Today it sits awkwardly between "describing" and "templating."
9. **Add a self-validation test: feed the output back to Claude.** Integration test in CI that takes the harvest output for a small fixture repo and prompts Claude with `"Implement <bean>"`. Diff the implementation against the original (semantic / AST distance). If the output isn't sufficient to reconstruct, the test fails. This makes "is the output any good?" an automated gate.
10. **Cross-link to upstream issue trackers / requirements docs.** If the cloned repo contains GitHub issues, a `REQUIREMENTS.md`, or an `adrs/` directory, surface those as first-class inputs and trace each bean back to them. The current pipeline ignores them.

---

## Documentation & metadata staleness (quick wins)

- **`README.md:3`** — "A desktop tool for mirroring git repositories, built with Python and PySide6." Wrong. Update to reflect that this is a requirements-harvester (CLI primary, GUI secondary). Add a usage example for `requirements-harvester harvest --repo <url>`.
- **`pyproject.toml:8`** — `description = "A desktop tool for mirroring git repositories"`. Same fix.
- **No harvester user docs.** No `docs/HARVESTER.md` explaining: what each stage produces, what a bean looks like, how to interpret coverage gates, what gaps mean, when/why to use `--llm-enabled`, what the output directory structure is.
- **CLAUDE.md (project root) does not reference the harvester at all.** Anyone joining the project would think it's a PySide6 GUI app. Add a top section calling out the harvester pipeline and pointing at the CLI entry point.

---

## Security / hardening

- **Stale default LLM model.** `cli.py:128` defaults to `claude-sonnet-4-20250514` (Sonnet 4.0). As of 2026-05-01, the latest Sonnet is `claude-sonnet-4-6` (Sonnet 4.6 from 2026-04). Bump the default and verify availability across all enrichment call sites.
- **Git URL is passed to `git clone` without an argument-terminator.** `harvester/git_ops.py:122` builds `["git", "clone", "--progress", url, str(workdir)]`. A URL beginning with `-` (e.g., `--upload-pack=...`) could be parsed as a flag by git. Fix: `["git", "clone", "--progress", "--", url, str(workdir)]`. Also worth validating the URL scheme (`https://`, `ssh://`, `git@`, or absolute local path) before invoking. Same fix needed in `services/clone_service.py` if it shells out independently.
- **CLI accepts `--repo` with no validation.** The GUI calls `validate_git_url` (`views/main_window.py:115`); the CLI (`cli.py:64-67`) does not. Wire the same validator into `HarvestConfig` construction so both entry points enforce the same policy.
- **No total-size cap on cloned repo.** `--max-file-bytes` (cli.py:91) bounds *per-file* read size, but a malicious repo with many small files (or a deep history) could still exhaust disk. Add a `--max-total-bytes` and check after clone, before inventory.
- **LLM prompt-injection from repo content is not mitigated.** `harvester/llm/enrichment.py` and `prompts.py` feed source code (untrusted) into Claude prompts. Wrap repo-derived content in delimited XML tags (`<repo_code>...</repo_code>`) and add a system-prompt instruction that anything inside those tags is data, not instructions. Document this assumption.
- **API key handling.** `cli.py:121-125` accepts `--llm-api-key` on the command line (visible in `ps`, shell history). Prefer env-var-only (`ANTHROPIC_API_KEY`) and remove the CLI flag, or warn loudly when the flag is used.

---

## Code quality

- **Broad `except Exception` per stage.** `harvester/pipeline.py` lines 201, 231, 262, 298, 318, 338, 362, 391 — every stage wraps its body in a generic `except Exception`. This makes debugging hard (a typo and a real domain error look identical) and could swallow programming bugs as if they were transient pipeline failures. Tighten each stage to catch its own domain-specific exceptions (`GitCloneError`, `GitRefError`, `OSError`, etc.) and let unexpected exceptions propagate.
- **Large analyzer files mixing many frameworks.** Top offenders:
  - `harvester/analyzers/models.py` — 951 LOC
  - `harvester/beans/templates.py` — 947 LOC
  - `harvester/analyzers/auth.py` — 829 LOC
  - `harvester/analyzers/apis.py` — 800 LOC
  - `harvester/pipeline.py` — 761 LOC

  Split by framework: `analyzers/models/{prisma,sqlalchemy,django,ef,...}.py` with a thin dispatcher in `models/__init__.py`. Same shape for auth, apis, components. Easier to add a new framework, easier to test, easier to read.
- **Regex duplication across analyzers.** Several files independently compile near-identical patterns (e.g., the TS/JS file extension regex, Flask route patterns, etc.). Extract into `analyzers/_patterns.py` so additions/fixes happen in one place.
- **`pipeline.py` resume logic re-runs B/C/F/G silently.** Lines 247-249, 273-275, 376-378, 402-404 — when a stage is "done," the code still re-runs the analyzer/report functions because intermediate state isn't actually persisted. The "skip" branch logs `stage_skipped_resume` but does the work anyway. Either persist stage outputs to disk (and rehydrate) or drop the misleading skip branches.
- **Pipeline state bookkeeping uses optional locals.** Lines 186-193 declare every stage output as `| None` and rely on careful sequencing. A `StageOutputs` dataclass updated stage-by-stage would express invariants and play better with mypy strict.
- **GUI exposes ~20% of CLI options.** `views/main_window.py` only takes a project name and URL. There's no way to: enable LLM enrichment, set output dir, configure include/exclude globs, set max-file-bytes, or resume a prior run. Either expand the GUI to match, or rebrand it as a "quick start" launcher and route advanced options to CLI.

---

## Tests

- **50 unit tests, ~all isolated regex/detector tests.** `tests/conftest.py` is minimal; individual tests load source-string fragments and assert detector output. There is **no integration test** that runs the full pipeline against a fixture Git repo (e.g., a checked-in sample project under `tests/fixtures/sample-django-app/`) and validates the bean output structurally.
- **No bean-quality assertions.** Tests verify "we produce a bean" but not "the bean is sufficient." Coupled with item 9 above, the harvester has no automated way to know whether its output is actually useful.
- **No GUI integration test beyond smoke.** `test_main_window.py` and `test_smoke.py` exist; depth unverified.

### Recommendations

- Add `tests/fixtures/sample-projects/` with 1–2 small but realistic checked-in repos (one Python/Flask, one TS/Next.js) and an integration test that runs the full pipeline end-to-end and asserts on the output tree.
- Add a "snapshot" test for the generated `REQUIREMENTS.md` (once it exists) so its shape is stable.

---

## Dead code / vestigial pieces

- **`src/repo_mirror_kit/harvester/runtime_verify/__init__.py`** — only contains `from __future__ import annotations`. No other files in the directory, no imports anywhere in the codebase. Either implement it or delete the directory.
- **`workers/clone_worker.py`** vs the harvester's own clone — the GUI clones via `services/clone_service.py` for the "Fetch" step, then `HarvestWorker` clones again inside the harvester pipeline. Verify: is the first clone redundant when the user proceeds to "Generate Requirements"? If so, share the clone artifact.
- **Manifest staleness.** `manifest.json:1-3` records `run_id: 20260214-141943` and `library_version: d16bd3b`. Confirm whether this should be regenerated by `/compile-team` (CLAUDE.md says **don't** regenerate this project's CLAUDE.md, but the manifest may be different). If it's a one-time scaffold trace, label it as such; if not, regenerate.

---

## Suggested execution order

If addressing this in vertical slices:

1. **Truth in advertising (1 hour).** Update README + pyproject description. Update root CLAUDE.md to mention the harvester. Bump LLM model default.
2. **Security hardening (1-2 hours).** Add `--` to git clone args. Wire `validate_git_url` into CLI config. Drop `--llm-api-key` flag.
3. **Tighten pipeline (half a day).** Replace generic `except Exception` per stage with domain exceptions. Either persist stage outputs or remove the misleading "skip" branches.
4. **Goal-alignment slice 1 (~1 day).** Add a top-level `REQUIREMENTS.md` generator that aggregates beans by domain, plus `.env.example` and `RUNBOOK.md` from existing analyzer output. No new analyzers required.
5. **Goal-alignment slice 2 (~1-2 days).** Promote LLM enrichment to default-on with a clean failure mode if no API key. Add a behavioral-spec analyzer mining docstrings + test names. Add an integration test against a fixture repo.
6. **Refactor pass.** Split the 4 largest analyzers by framework. Extract shared regex patterns. Delete `runtime_verify/` (or implement it).
