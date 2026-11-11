# Real-world triage: `miguelgrinberg/microblog` (2026-11-11)

A held-out, medium-sized, MIT-licensed Flask app (users, posts, followers, messages, notifications, i18n, JSON API, background tasks; 74 files) harvested with `--no-llm` to expose idiom gaps the toy fixtures hide.

## Before → after this session's fixes

| Signal | First harvest | After fixes |
|--------|--------------|-------------|
| API paths | every route under `/api` (blueprint-name collision: all blueprints are called `bp`) | correct: `/auth/*`, `/api/*`, `/` |
| Models with fields | 5 models, **0 fields** (SQLAlchemy 2.0 `Mapped[...]`) | 5 models, all columns, constraints, FKs, 1:N / N:1 relationships |
| Screens | 4 noisy template screens (`base`, macros) with no fields | 8 WTForms screens with fields, validators, routes, form-post contracts; layouts/partials skipped |
| Form-post request contracts | unknown | declared from the form (source `form`) |
| Fidelity gates | n/a | request contracts 100%, model fields 100%, relationships 100%, screen→model mappings 33% (action-named forms like Login have no 1:1 model) |

## Fixed in this session
- Router identity is `(defining module, variable)` resolved through imports (was variable name only) — `python_prefixes.py`.
- SQLAlchemy 2.0 declarative models (`Mapped`, `mapped_column`, `relationship`, `ForeignKey(User.id)`).
- WTForms/Flask-WTF forms → `ScreenSurface`s linked to handlers, plus form-derived request contracts; model binding by column overlap, with honest gaps.
- Template layouts/partials/macro libraries are no longer reported as screens.

## Still open (new beans)

| Bean | Gap | Observed effect |
|------|-----|-----------------|
| BEAN-082 | HTML page routes (`render_template`/`redirect`) typed as APIs with unknown responses | `api_response_contracts` 8.6% |
| BEAN-083 | SQLAlchemy Core association tables (`followers`) | N:M table missing from DDL/ER |
| BEAN-084 | Feature clustering splits action-named routes into one-route features | 20 features, many of size 1–3 |
| BEAN-085 | JS/TS ORMs (Mongoose, Drizzle, Sequelize define) | no models → no DB bundle/mapping for those stacks |
| BEAN-086 | Template ↔ form ↔ context tracing | template screens show no fields; duplicates with WTForms screens |

Not attempted: i18n catalogs, pagination behaviour, background-task semantics (RQ), search backend integration — these need the agentic enrichment pass (BEAN-068) run live.

## Method note
No code from the target repo is vendored here; the harvest output lived in a scratch directory. Re-run with `git clone https://github.com/miguelgrinberg/microblog && requirements-harvester harvest --repo ./microblog --out out --no-llm`.
