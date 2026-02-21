# Task 06: Add Stage G to Pipeline

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Depends On** | 5 |
| **Status** | Done |
| **Started** | 2026-02-21 00:43 |
| **Completed** | 2026-02-21 00:43 |
| **Duration** | < 1m |

## Goal

Wire Stage G into the pipeline after Stage F.

## Definition of Done

- [x] "G" added to STAGE_NAMES list
- [x] `_run_stage_g()` method implemented in HarvestPipeline
- [x] Stage G runs after Stage F in the pipeline flow
- [x] Stage G supports resume (skip if done, re-run if resumed)
- [x] `HarvestResult.generated_file_count` field added
- [x] Pipeline reports generated file count in completion log
- [x] `_derive_project_name()` extracts project name from repo URL
- [x] Pipeline tests updated for 8 stages