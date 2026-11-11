"""Rebuild-and-score loop (IMP-09 / forgeSetup WP-3.4).

The harvester's north star is "requirements sufficient to *recreate* the
project". This subpackage closes the measurement gap with the cheapest
fidelity signal available today:

    harvest  →  rebuild(lane)  →  score

- :mod:`.executor` drives an agentic rebuild from a harvest output directory
  into a fresh workspace and records run telemetry (wall time, tokens/cost or
  retries). Cloud lane: Claude Code headless. Local lane: forge-loop over the
  requirements. Actual runs are Forge WP-3.5.
- :mod:`.scoring` re-harvests the rebuild and diffs the two surface
  collections — tier-1 "surface re-extraction diff": did the rebuild
  reproduce the same routes, models, APIs, auth surfaces?

This is the buildable-now first slice of the BEAN-078 rebuild-eval harness,
whose heavier behavioral-parity scoring (Gherkin pass-rate, golden replay,
schema diff) waits on BEAN-071/074/077. Surface diff is scoring *tier 1*;
those are tiers 2 and 3.
"""

from repo_mirror_kit.harvester.rebuild.scoring import (
    CategoryScore,
    ScoreReport,
    diff_harvest_dirs,
    load_surfaces,
    score_surfaces,
)

__all__ = [
    "CategoryScore",
    "ScoreReport",
    "diff_harvest_dirs",
    "load_surfaces",
    "score_surfaces",
]
