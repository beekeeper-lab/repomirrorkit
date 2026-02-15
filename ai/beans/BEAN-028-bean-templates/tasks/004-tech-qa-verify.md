# Task 004: Tech QA — Verify Acceptance Criteria

**Owner:** Tech QA
**Status:** Done
**Depends On:** 003

## Verification Checklist

- [ ] `ruff check src/ tests/` passes
- [ ] `ruff format --check src/ tests/` passes
- [ ] `mypy src/` passes (strict mode)
- [ ] `pytest` passes (all tests green)
- [ ] Template functions exist for all 7 bean types
- [ ] Each template produces YAML frontmatter with id, type, title, source_refs, traceability, status
- [ ] Page/Route template has 8 required sections
- [ ] Component template has 6 required sections
- [ ] API template has 8 required sections
- [ ] Model template has 6 required sections
- [ ] Auth template has 4 required sections
- [ ] Config template has 4 required sections
- [ ] Crosscutting template has concern-specific sections
