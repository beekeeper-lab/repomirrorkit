# SPEC — Mirror Mode: Self-Contained, Rebuild-Grade Output

**Created:** 2026-07-11
**Status:** Proposed (awaiting approval / bean decomposition)
**Builds on:** `ROADMAP-RECREATION.md` (2026-07-03) — this spec does not replace the roadmap; it adds the net-new "mirror mode" work and sequences the existing recreation beans behind the user's actual goal.

---

## 1. Goal

Point RepoMirrorKit at any Git repo the user can read, and get back an output
directory that is a **self-contained requirements package**:

1. **No original source.** The final pipeline stage deletes `<out>/repo/` —
   including its `.git/` — so the package contains zero source code and zero
   Git history (no accidental pushes, no license contamination, no
   transliteration shortcut for the rebuilding agent).
2. **Sufficient to rebuild.** An agent given *only* the output directory can
   implement every bean, in any stack (Vue, React, Flutter, …), and produce an
   application **functionally identical** to the original. Visual design is
   explicitly out of scope; behavior, contracts, data, screens-as-functions,
   business rules, navigation, and seed data are in scope.
3. **Measurably identical.** A generated, stack-agnostic Gherkin acceptance
   suite is the parity measuring stick for comparing rebuilds against each
   other (the model-comparison / long-run experiment rig).

### Decisions locked 2026-07-11

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Rules verbatim, no code.** Beans capture exact business rules — regexes, formulas (as neutral expressions), enum values, thresholds, defaults, error messages, status codes — but never source-code blocks. | Exactness without stack bias; agents reimplement instead of transliterating. |
| D2 | **Gherkin acceptance suite** is the parity artifact (elevates BEAN-074). | Makes "functionally identical" testable across stacks. |
| D3 | **`--mirror` mode requires `ANTHROPIC_API_KEY`** and fails fast (exit 3) without it. Default `harvest` keeps today's warn-and-degrade behavior. | Structural-only output can't reach mirror grade; quick scans stay cheap. |
| D4 | **Cleanup is a new final stage (Stage H)**, default-on in mirror mode, opt-out via `--keep-source`, opt-in outside mirror via `--cleanup`. | The user's core ask; also makes BEAN-078's "rebuild from output alone" premise enforced by construction. |

---

## 2. Current state (verified against code, 2026-07-11)

- Pipeline stages are `A B C C2 D E F G` (`pipeline.py:84`). Nothing re-reads
  `<out>/repo/` after Stage G — `data-model.md` re-reads source during Stage F
  (`data_model.py:81-92`), OpenAPI/env/runbook use in-memory surfaces. **A
  post-run delete breaks no generation step.**
- All `source_refs` are repo-root-relative POSIX paths (`inventory.py:270-271`);
  no artifact embeds `<out>/repo/` absolute paths. After deletion they become
  **provenance pointers** — semantically valid against the original repo, not
  resolvable locally. No provenance (URL + commit SHA) is currently recorded.
- **`--resume` breaks after cleanup:** Stage A marked done → pipeline
  reconstructs a clone_result pointing at the missing `repo/`
  (`pipeline.py:256-265`) and Stage B fails on OSError.
- **Missing key silently downgrades** `llm_enabled` with a stderr warning
  (`config.py:107-126`).
- **Beans contain no code excerpts today** (seed-data value tables are the only
  embedded data). Templates hardcode many `TODO:` placeholders (Validation
  rules, Errors, Examples, Open questions — `templates.py`), so the
  `placeholder_free_beans` fidelity metric (`fidelity.py:160-169`, threshold
  0.0/informational) can essentially never reach 100% on structural runs.
- Fidelity metrics exist (BEAN-076, `fidelity.py:40-47`): request/response
  contracts 60/60, model_fields 80, model_relationships 50,
  screen_field_mappings **hardcoded N/A** (blocked on BEAN-064),
  placeholder_free_beans informational.
- Extraction depth: API contracts are Python-only (BEAN-062: FastAPI declared /
  Flask inferred; field name+type+required; **no validation rules, error
  schemas, or examples**). Models: fields + column types + PK/not-null/unique +
  FK edges; **no defaults, enums, check constraints, or app-level validation**.
- The only `shutil.rmtree` is the failed-clone size-cap path
  (`git_ops.py:182`). There is **no cleanup stage and no bean for one** — it is
  net-new, as is provenance capture and the `--mirror` profile.
- Relevant roadmap beans: **Done:** 062, 066, 070, 071, 076 (·079 in
  progress). **Unapproved:** 060, 061, 063, 064, 065, 067, 068, 069, 072, 073,
  074, 075, 077, 078.

---

## 3. Target state

```
requirements-harvester harvest --repo <url> --mirror --out ./out
```

produces `./out` containing **only**:

```
out/
├── REQUIREMENTS.md          # front door + provenance header (URL, SHA, date)
├── beans/BEAN-*.md          # self-contained, framework-neutral, zero TODO:
├── features/FEAT-*.md       # feature clusters (BEAN-069)
├── build-manifest.json      # dependency-ordered executable bean plan (BEAN-069)
├── parity/features/*.feature# stack-agnostic Gherkin suite (BEAN-074+)
├── api-contract.json        # OpenAPI 3.1
├── db/                      # SQL DDL + JSON Schema + seed data (BEAN-072)
├── screens/                 # screen spec YAML + nav map (BEAN-073)
├── surface-map.{md,json}, data-model.md, .env.example, RUNBOOK.md
├── project-folder/          # Claude Code scaffold
├── reports/                 # inventory, coverage, gaps, traceability
└── state/state.json         # includes provenance + cleanup record
                             # NO repo/, NO .git anywhere
```

An implementing agent works through `build-manifest.json` bean-by-bean; the
rebuilt app is judged by the `parity/` Gherkin suite. Different stacks, same
behavior.

---

## 4. Phases

Phasing rule: each phase is independently shippable and useful; Phase 1 alone
delivers the cleanup ask end-to-end.

### Phase 1 — `--mirror` mode + Stage H cleanup *(net-new; no dependencies; ship first)*

**M1.1 — Config & CLI surface**
- `HarvestConfig.mirror: bool = False`, `keep_source: bool = False`,
  `cleanup: bool | None = None` (resolved: mirror → on, else off, `--cleanup`
  forces on, `--keep-source` forces off and wins).
- `--mirror` semantics in `__post_init__` / CLI (`cli.py`, `config.py`):
  - `ANTHROPIC_API_KEY` missing or `anthropic` package absent → **hard error,
    exit 3** with an actionable message (replaces warn-and-degrade *only* in
    mirror mode).
  - Forces `llm_enabled=True`; flips `--fail-on-fidelity` default to **true**;
    selects the **mirror fidelity threshold profile** (Phase 5, M5.1 — ships a
    minimal version here so the flag is honest from day one).

**M1.2 — Provenance capture (Stage A)**
- `CloneResult` gains `head_sha` (`git rev-parse HEAD` after checkout,
  `git_ops.py`).
- Persist `{repo_url, ref, head_sha, harvested_at}` into `state.json` and
  render a provenance block at the top of `REQUIREMENTS.md`:
  *"Source references (`path:line`) refer to `<url>` @ `<sha>`; the source tree
  is not included in this package."*
- This is what keeps every `source_refs` entry meaningful after deletion.

**M1.3 — Stage H: cleanup (`harvester/cleanup.py`, new)**
- Runs **only after Stages A–G all succeed** (any failure skips cleanup so the
  working copy survives for debugging).
- Safety invariants, all mandatory, in order:
  1. Target is exactly `output_dir / "repo"`, `resolve()`d, must remain inside
     `output_dir`, must not be a symlink.
  2. `state.json` must record that Stage A cloned into this directory during
     this run (or a prior run of the same output dir). Never delete a `repo/`
     the harvester didn't create.
  3. Sanity check the target contains `.git/` (it's a clone, not user data);
     if state confirms the clone but `.git` is absent, proceed with a warning.
  4. `shutil.rmtree` the directory; then walk `output_dir` and **assert no
     `.git` remains anywhere** (guards future generators too). Fail loudly if
     one is found.
- Record `{removed: true, files_removed, bytes_freed, completed_at}` in
  `state.json`; append `"H"` to the stage list (`pipeline.py:84`) and to
  `StateManager` stages; structlog summary line.

**M1.4 — Resume semantics after cleanup**
- `--resume` with `repo/` missing → **force re-clone** instead of failing in
  Stage B (fix at `pipeline.py:256-265`: treat Stage A as not-done when the
  workdir is absent).
- If provenance `head_sha` exists and the re-cloned HEAD differs (and no
  `--ref` pins it), log a drift warning: recorded line numbers may no longer
  match.

**M1.5 — Tests (fixture-based)**
- Unit: every cleanup safety invariant (wrong dir, symlink, no state record,
  missing `.git`, failure-path skip).
- Integration on `python-flask` fixture: mirror run → `repo/` absent, zero
  `.git` under `out/`, beans present, provenance in `state.json` and
  `REQUIREMENTS.md`; `--keep-source` preserves `repo/`; `--resume` on a cleaned
  dir re-clones and completes.
- Exit-code matrix: mirror without key → 3; gaps → 2; fidelity fail → 4.

**Files touched:** `cli.py`, `config.py`, `pipeline.py`, `state.py`,
`git_ops.py`, `generator/requirements_md.py`, new `cleanup.py`, tests.

### Phase 2 — Verbatim rule capture *(D1: exactness without code)*

**M2.1 — Policy (document in bean-workflow + templates docstrings)**
Verbatim = exact literals copied into structured fields: regex patterns,
numeric thresholds/limits, enum members, default values, error-message
strings, HTTP status codes, and formulas re-expressed as framework-neutral
expressions (`total = subtotal * (1 + tax_rate)` — never a pasted source
statement or block). PII-bearing literals (real emails, names in fixtures) and
secret-shaped values are redacted per the cross-cutting safety rules — **and
every redaction is surfaced to the operator** (M2.5); silent redaction hides a
finding the repo owner needs to act on.

**M2.2 — Template upgrades (`beans/templates.py`)**
- `## Validation rules` becomes a table: Field | Rule | Exact value/pattern |
  Error message | Confidence.
- `## Errors` becomes a table: Condition | Status | Error body/message.
- **Placeholder policy:** every section that would render `TODO:` either gets
  real data or is converted into an explicit `gaps:` frontmatter entry +
  `## Gaps & unknowns` line. In mirror output the literal `TODO:` must not
  appear — this is what makes `placeholder_free_beans = 100%` achievable and
  honest (absence is *declared*, not silent).

**M2.3 — Analyzer depth for exact values**
- `api_contracts.py`: capture error responses (Flask `abort(code)`, FastAPI
  `HTTPException(status_code=…, detail=…)`, returned status tuples) and
  response status codes.
- Model analyzers: defaults, enum column types, check constraints, indexes.
- BEAN-065 (`BusinessRuleSurface`) implements the general mining
  (pydantic/marshmallow validators now; zod/yup/etc. once BEAN-061/063 land)
  and adopts the verbatim policy as its output contract.

**M2.4 — LLM prompt contract (`llm/prompts.py`)**
- Enrichment must quote exact values, never emit code blocks, express
  algorithms as neutral given/when/then or expressions, and return a new
  `exact_rules: [{subject, rule, value, error_message, source_ref}]` field
  that templates render into M2.2's tables.

**M2.5 — Sensitive-findings surfacing (operator visibility)**
- Every literal captured by M2.3/M2.4 and by seed-data extraction (BEAN-066)
  passes through detectors (secret-shaped: key patterns, high-entropy strings,
  connection strings; PII-shaped: emails, phone numbers, person-name fixture
  fields) **before** being written into any bean.
- Redaction replaces the value with a typed placeholder, e.g.
  `[REDACTED:aws-access-key]`, `[REDACTED:email]`.
- **The value itself is never written anywhere** — not in beans, not in logs,
  not in the findings report (cross-cutting rules 1–2). Each finding records
  only: category (secret/PII), detector kind, `file:line` in the original repo
  (meaningful via M1.2 provenance), the affected surface/bean, and the
  placeholder used. A short content-hash prefix may be stored for dedup.
- Surfacing, three places:
  1. `reports/sensitive-findings.{md,json}` — one row per finding.
  2. A prominent end-of-run CLI warning: *"⚠ N sensitive values were found in
     the source repo and redacted — see reports/sensitive-findings.md.
     Secrets in source are a bad practice; rotate any real credentials."*
  3. A one-line rollup in `REQUIREMENTS.md` (count + pointer, no locations).
- Findings do **not** change the exit code (the harvest succeeded); a
  `--fail-on-secrets` gate can be added later if CI wants to enforce it.

### Phase 3 — Contract & screen completeness *(execute existing roadmap beans)*

Approve and run, in roadmap wave order: **BEAN-061** (tree-sitter),
**BEAN-063** (JS/TS API contracts), **BEAN-064** (ScreenSurface + field→model
mapping — unblocks the N/A `screen_field_mappings` metric), **BEAN-067**
(workflows/state machines), **BEAN-068** (agentic enrichment v2),
**BEAN-069** (feature clustering → `features/FEAT-*.md` + `build-manifest.json`).

Mirror-mode addition on top of BEAN-069: `build-manifest.json` is the
**executable plan** — a dependency-ordered DAG of bean IDs with per-bean
verification pointers (which Gherkin scenarios prove it). This is the "beans
that can be run and executed" contract.

### Phase 4 — Parity suite *(D2: the measuring stick)*

- **BEAN-074** (Gherkin per feature cluster) with mirror additions:
  - Output under `parity/features/*.feature` + `parity/README.md` (how to
    wire the suite to any rebuilt app: each scenario is UI/API-observable
    behavior, no framework nouns, no CSS selectors, no route-shape
    assumptions).
  - Scenario tags trace to beans (`@BEAN-012`) and features (`@FEAT-03`) —
    keeps the traceability chain (bean → criterion → scenario) machine-checkable.
- Supporting design artifacts: **BEAN-072** (DB bundle), **BEAN-073** (screen
  YAML + nav map); **BEAN-075** (diagrams) optional, human-review only.
- **BEAN-077** (golden parity fixtures) starts here — it's independent and
  feeds Phase 5.

### Phase 5 — Mirror gates + rebuild eval *(closes the loop)*

**M5.1 — Mirror fidelity threshold profile** (`fidelity.py`; selected by
`--mirror`, defaults unchanged otherwise):

| Metric | Default | Mirror |
|--------|---------|--------|
| api_request_contracts | 60 | 90 |
| api_response_contracts | 60 | 90 |
| model_fields | 80 | 100 |
| model_relationships | 50 | 80 |
| screen_field_mappings | 60 (N/A) | 80 (applicable after BEAN-064) |
| placeholder_free_beans | informational | **100, hard gate** |

`--fail-on-fidelity` defaults true in mirror mode (exit 4 on failure).

**M5.2 — BEAN-078 rebuild eval harness.** Agent rebuilds the fixture **from
the output directory alone** — Stage H makes "alone" literal. Parity score =
Gherkin pass-rate + golden replay (BEAN-077) + schema diff. Telemetry keyed by
(model, stack, instructions) — this *is* the model-comparison and
long-run-experiment rig.

**M5.3 — CI.** Mirror-mode harvest of both fixtures (`python-flask`,
`ts-next`) on every merge to `test`; fidelity gates fail regression.

---

## 5. Definition of done (overall)

- [ ] `harvest --repo <fixture> --mirror` exits 0/2 with `repo/` gone and zero
      `.git` anywhere under the output directory.
- [ ] Provenance (URL, SHA, date) recorded in `state.json` and `REQUIREMENTS.md`;
      `--resume` on a cleaned dir re-clones instead of failing.
- [ ] Mirror-run beans contain zero `TODO:`; unknowns appear as declared gaps.
- [ ] Exact-rule tables (validation, errors, defaults, enums) populated for
      both fixtures; no source-code blocks anywhere in beans.
- [ ] Secrets/PII in source are redacted to typed placeholders **and** reported
      to the operator (`reports/sensitive-findings.md` + CLI warning); raw
      values appear nowhere in the output or logs.
- [ ] `build-manifest.json` orders all beans as an executable DAG with
      per-bean Gherkin verification pointers.
- [ ] BEAN-078 harness: agent rebuild from output alone scores ≥90% Gherkin
      scenarios on both fixtures.
- [ ] Mirror fidelity gates run in CI and fail on regression.

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Cleanup deletes a directory the user cared about (`--out` misuse) | Low | High | M1.3 invariants: only `<out>/repo`, only if state records our clone, `.git` sanity check, never on failed runs |
| LLM cost/latency on large repos in mirror mode | Med | Med | BEAN-068 Batch API; per-surface caching; `--max-*` caps already exist |
| Verbatim literals leak secrets/PII from source into beans | Med | High | M2.5 detect → redact → surface: typed placeholders in beans, findings report + CLI warning for the operator, values never persisted anywhere; Security Engineer review (cross-cutting rule 7) |
| Regex extraction ceiling until BEAN-061 lands | High | Med | Mirror gates make the shortfall visible as declared gaps, not silent |
| `placeholder_free = 100%` gamed by converting everything to gaps | Med | Med | Pair with contract-coverage gates (90/100) so gaps can't hide missing contracts |
| Stage H stage-list change breaks `state.json` back-compat | Low | Low | StateManager tolerates unknown/extra stages; add migration test |

## 7. Out of scope

- Visual fidelity (unchanged from the recreation roadmap).
- Multi-repo / monorepo-split harvesting.
- Flipping cleanup default-on for non-mirror runs (revisit after Phase 1 soak).

## 8. Bean decomposition proposal

Net-new beans (to be created via `/new-bean`): **M1** → one bean
("`--mirror` mode + Stage H cleanup + provenance + resume fix" — small enough
to stay one vertical slice), **M2** → three beans (templates + placeholder
policy; analyzer/prompt exactness; **M2.5 sensitive-findings detect → redact →
surface**). Phases 3–5 reuse existing beans 061–078 with the mirror acceptance
criteria above appended; M5.1 is a small amendment to BEAN-076's
implementation.
