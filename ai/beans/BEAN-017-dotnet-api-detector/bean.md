# BEAN-017: .NET API Detector

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-017 |
| **Status** | Approved |
| **Priority** | Medium |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to detect .NET backend projects (minimal APIs, ASP.NET) to activate .NET-specific endpoint and model analyzers. .NET projects have distinct file patterns (`.csproj`, `Program.cs`, `appsettings.json`) and framework conventions.

## Goal

Implement a .NET API detector that identifies ASP.NET and minimal API projects by examining `.csproj` files, `Program.cs`, configuration files, and controller patterns.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/detectors/dotnet_api.py`
- Detect .NET backends via:
  - `*.csproj` file presence with web SDK references (`Microsoft.NET.Sdk.Web`)
  - `Program.cs` with `WebApplication.CreateBuilder` or `Host.CreateDefaultBuilder`
  - `appsettings.json` and `appsettings.*.json` files
  - Controller patterns: `*Controller.cs` files, `[ApiController]` attribute
  - `Startup.cs` (older pattern)
  - Minimal API patterns: `app.MapGet()`, `app.MapPost()`
- Basic detection for v1
- Confidence scoring and evidence collection
- Register with detector framework
- Unit tests

### Out of Scope
- .NET MAUI or WPF detection
- Blazor detection
- Entity Framework detection (covered by BEAN-018 data detector)
- Actual endpoint extraction (BEAN-022)

## Acceptance Criteria

- [ ] `DotnetApiDetector` implements the `Detector` interface
- [ ] Detects .NET via `.csproj` with web SDK reference
- [ ] Detects .NET via `Program.cs` patterns
- [ ] Detects .NET via controller file patterns
- [ ] Detects minimal API patterns
- [ ] Confidence scoring based on evidence strength
- [ ] No false positives on .NET library or console app projects
- [ ] Unit tests cover: ASP.NET repo, minimal API repo, non-web .NET repo
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-010 (Detector Framework).
- Spec marks .NET as "basic" support for v1 ("minimal/ASP.NET basic").
- Reference: Spec section 2.1.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 |      |       |          |           |            |

| Metric | Value |
|--------|-------|
| **Total Tasks** | — |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |
