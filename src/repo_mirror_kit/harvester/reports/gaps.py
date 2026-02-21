"""Gap hunt queries and gap report generation.

Implements spec section 7.3: identifies surfaces missing bean coverage,
beans missing acceptance criteria, undocumented APIs, unlinked models,
unreported env vars, and uncovered auth surfaces. Produces
``reports/gaps.md`` with actionable gap entries.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.beans.writer import WrittenBean

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GapEntry:
    """A single gap finding.

    Attributes:
        category: Gap query category (e.g. "Routes with no bean").
        description: What is missing.
        file_path: Source file path where the gap is located.
        recommended_action: Actionable suggestion to close the gap.
    """

    category: str
    description: str
    file_path: str
    recommended_action: str


@dataclass(frozen=True)
class GapReport:
    """Collection of all gap hunt results.

    Attributes:
        entries: All gap entries found across all queries.
        total_gaps: Total number of gaps found.
    """

    entries: list[GapEntry]

    @property
    def total_gaps(self) -> int:
        """Return total number of gap entries."""
        return len(self.entries)


# ---------------------------------------------------------------------------
# Gap hunt queries (spec section 7.3)
# ---------------------------------------------------------------------------


def find_routes_without_bean(
    surfaces: SurfaceCollection,
    beans: list[WrittenBean],
) -> list[GapEntry]:
    """Find routes that have no corresponding bean.

    Args:
        surfaces: Extracted surfaces.
        beans: Written bean records.

    Returns:
        List of gap entries for uncovered routes.
    """
    covered_names = {b.title for b in beans if b.surface_type == "route"}
    entries: list[GapEntry] = []
    for route in surfaces.routes:
        if route.name not in covered_names:
            file_path = (
                route.source_refs[0].file_path if route.source_refs else "unknown"
            )
            entries.append(
                GapEntry(
                    category="Routes with no bean",
                    description=f"Route '{route.name}' ({route.method} {route.path}) has no bean",
                    file_path=file_path,
                    recommended_action=f"Create a page bean for route '{route.name}'",
                )
            )
    return entries


def find_beans_missing_acceptance_criteria(
    beans: list[WrittenBean],
) -> list[GapEntry]:
    """Find beans whose markdown files lack acceptance criteria checkboxes.

    Scans each bean file for ``- [ ]`` patterns indicating acceptance
    criteria. Beans without any are flagged.

    Args:
        beans: Written bean records.

    Returns:
        List of gap entries for beans missing acceptance criteria.
    """
    entries: list[GapEntry] = []
    for bean in beans:
        if bean.skipped:
            continue
        if not bean.path.exists():
            continue
        content = bean.path.read_text(encoding="utf-8")
        if "- [ ]" not in content:
            entries.append(
                GapEntry(
                    category="Beans missing acceptance criteria",
                    description=f"Bean {bean.bean_id} '{bean.title}' has no acceptance criteria",
                    file_path=str(bean.path),
                    recommended_action=f"Add acceptance criteria (- [ ] ...) to {bean.bean_id}",
                )
            )
    return entries


def find_apis_without_description(
    surfaces: SurfaceCollection,
) -> list[GapEntry]:
    """Find API surfaces with no request or response schema.

    Args:
        surfaces: Extracted surfaces.

    Returns:
        List of gap entries for undocumented APIs.
    """
    entries: list[GapEntry] = []
    for api in surfaces.apis:
        if not api.request_schema and not api.response_schema:
            file_path = api.source_refs[0].file_path if api.source_refs else "unknown"
            entries.append(
                GapEntry(
                    category="APIs with no request/response description",
                    description=(
                        f"API '{api.name}' ({api.method} {api.path}) "
                        f"has no request or response schema"
                    ),
                    file_path=file_path,
                    recommended_action=f"Document request/response schemas for '{api.name}'",
                )
            )
    return entries


def find_models_referenced_but_undocumented(
    surfaces: SurfaceCollection,
    beans: list[WrittenBean],
) -> list[GapEntry]:
    """Find models referenced by APIs but not documented with a bean.

    Checks API surfaces for model references in request/response schemas
    and cross-references with model beans.

    Args:
        surfaces: Extracted surfaces.
        beans: Written bean records.

    Returns:
        List of gap entries for undocumented referenced models.
    """
    # Collect documented model names from beans
    documented_models = {b.title for b in beans if b.surface_type == "model"}
    # Also collect model names from model surfaces
    known_model_names = {m.name for m in surfaces.models}

    entries: list[GapEntry] = []
    for api in surfaces.apis:
        # Extract model references from schemas
        referenced = _extract_model_refs(api)
        for ref_name in referenced:
            if ref_name in known_model_names and ref_name not in documented_models:
                file_path = (
                    api.source_refs[0].file_path if api.source_refs else "unknown"
                )
                entries.append(
                    GapEntry(
                        category="Models referenced by APIs but not documented",
                        description=(
                            f"Model '{ref_name}' is referenced by API '{api.name}' "
                            f"but has no bean"
                        ),
                        file_path=file_path,
                        recommended_action=f"Create a model bean for '{ref_name}'",
                    )
                )
    return entries


def find_env_vars_not_in_report(
    surfaces: SurfaceCollection,
    beans: list[WrittenBean],
) -> list[GapEntry]:
    """Find env vars referenced in code but not covered by a config bean.

    Args:
        surfaces: Extracted surfaces.
        beans: Written bean records.

    Returns:
        List of gap entries for unreported env vars.
    """
    covered_names = {b.title for b in beans if b.surface_type == "config"}
    entries: list[GapEntry] = []
    for cfg in surfaces.config:
        if cfg.name not in covered_names:
            file_path = cfg.source_refs[0].file_path if cfg.source_refs else "unknown"
            entries.append(
                GapEntry(
                    category="Env vars referenced but not in envvar report",
                    description=(
                        f"Env var '{cfg.env_var_name or cfg.name}' "
                        f"has no corresponding config bean"
                    ),
                    file_path=file_path,
                    recommended_action=(
                        f"Create a config bean documenting '{cfg.env_var_name or cfg.name}'"
                    ),
                )
            )
    return entries


def find_auth_checks_without_bean(
    surfaces: SurfaceCollection,
    beans: list[WrittenBean],
) -> list[GapEntry]:
    """Find auth surfaces with no corresponding auth bean.

    Args:
        surfaces: Extracted surfaces.
        beans: Written bean records.

    Returns:
        List of gap entries for uncovered auth surfaces.
    """
    covered_names = {b.title for b in beans if b.surface_type == "auth"}
    entries: list[GapEntry] = []
    for auth in surfaces.auth:
        if auth.name not in covered_names:
            file_path = auth.source_refs[0].file_path if auth.source_refs else "unknown"
            entries.append(
                GapEntry(
                    category="Auth checks present but no auth bean",
                    description=f"Auth surface '{auth.name}' has no corresponding bean",
                    file_path=file_path,
                    recommended_action=f"Create an auth bean for '{auth.name}'",
                )
            )
    return entries


def find_state_mgmt_without_bean(
    surfaces: SurfaceCollection,
    beans: list[WrittenBean],
) -> list[GapEntry]:
    """Find state management surfaces with no corresponding bean.

    Args:
        surfaces: Extracted surfaces.
        beans: Written bean records.

    Returns:
        List of gap entries for uncovered state management surfaces.
    """
    covered_names = {b.title for b in beans if b.surface_type == "state_mgmt"}
    entries: list[GapEntry] = []
    for sm in surfaces.state_mgmt:
        if sm.name not in covered_names:
            file_path = sm.source_refs[0].file_path if sm.source_refs else "unknown"
            entries.append(
                GapEntry(
                    category="State management with no bean",
                    description=f"State store '{sm.name}' ({sm.pattern}) has no corresponding bean",
                    file_path=file_path,
                    recommended_action=f"Create a state_mgmt bean for '{sm.name}'",
                )
            )
    return entries


def find_middleware_without_bean(
    surfaces: SurfaceCollection,
    beans: list[WrittenBean],
) -> list[GapEntry]:
    """Find middleware surfaces with no corresponding bean.

    Args:
        surfaces: Extracted surfaces.
        beans: Written bean records.

    Returns:
        List of gap entries for uncovered middleware surfaces.
    """
    covered_names = {b.title for b in beans if b.surface_type == "middleware"}
    entries: list[GapEntry] = []
    for mw in surfaces.middleware:
        if mw.name not in covered_names:
            file_path = mw.source_refs[0].file_path if mw.source_refs else "unknown"
            entries.append(
                GapEntry(
                    category="Middleware with no bean",
                    description=f"Middleware '{mw.name}' ({mw.middleware_type}) has no corresponding bean",
                    file_path=file_path,
                    recommended_action=f"Create a middleware bean for '{mw.name}'",
                )
            )
    return entries


def find_integrations_without_bean(
    surfaces: SurfaceCollection,
    beans: list[WrittenBean],
) -> list[GapEntry]:
    """Find integration surfaces with no corresponding bean.

    Args:
        surfaces: Extracted surfaces.
        beans: Written bean records.

    Returns:
        List of gap entries for uncovered integration surfaces.
    """
    covered_names = {b.title for b in beans if b.surface_type == "integration"}
    entries: list[GapEntry] = []
    for integ in surfaces.integrations:
        if integ.name not in covered_names:
            file_path = (
                integ.source_refs[0].file_path if integ.source_refs else "unknown"
            )
            entries.append(
                GapEntry(
                    category="Integrations with no bean",
                    description=f"Integration '{integ.name}' ({integ.integration_type}) has no corresponding bean",
                    file_path=file_path,
                    recommended_action=f"Create an integration bean for '{integ.name}'",
                )
            )
    return entries


def find_ui_flows_without_bean(
    surfaces: SurfaceCollection,
    beans: list[WrittenBean],
) -> list[GapEntry]:
    """Find UI flow surfaces with no corresponding bean.

    Args:
        surfaces: Extracted surfaces.
        beans: Written bean records.

    Returns:
        List of gap entries for uncovered UI flow surfaces.
    """
    covered_names = {b.title for b in beans if b.surface_type == "ui_flow"}
    entries: list[GapEntry] = []
    for flow in surfaces.ui_flows:
        if flow.name not in covered_names:
            file_path = flow.source_refs[0].file_path if flow.source_refs else "unknown"
            entries.append(
                GapEntry(
                    category="UI flows with no bean",
                    description=f"UI flow '{flow.name}' ({flow.flow_type}) has no corresponding bean",
                    file_path=file_path,
                    recommended_action=f"Create a ui_flow bean for '{flow.name}'",
                )
            )
    return entries


def find_dependencies_without_bean(
    surfaces: SurfaceCollection,
    beans: list[WrittenBean],
) -> list[GapEntry]:
    """Find dependency surfaces with no corresponding bean.

    Args:
        surfaces: Extracted surfaces.
        beans: Written bean records.

    Returns:
        List of gap entries for uncovered dependency surfaces.
    """
    covered_names = {b.title for b in beans if b.surface_type == "dependency"}
    entries: list[GapEntry] = []
    for dep in surfaces.dependencies:
        if dep.name not in covered_names:
            file_path = dep.source_refs[0].file_path if dep.source_refs else "unknown"
            entries.append(
                GapEntry(
                    category="Dependencies with no bean",
                    description=(
                        f"Dependency '{dep.name}' ({dep.purpose}) "
                        f"from {dep.manifest_file} has no corresponding bean"
                    ),
                    file_path=file_path,
                    recommended_action=f"Create a dependency bean for '{dep.name}'",
                )
            )
    return entries


def run_all_gap_queries(
    surfaces: SurfaceCollection,
    beans: list[WrittenBean],
) -> GapReport:
    """Run all 10 gap hunt queries and return a consolidated report.

    Args:
        surfaces: Extracted surfaces from analyzers.
        beans: Written bean records from the bean writer.

    Returns:
        A GapReport containing all gap entries.
    """
    entries: list[GapEntry] = []
    entries.extend(find_routes_without_bean(surfaces, beans))
    entries.extend(find_beans_missing_acceptance_criteria(beans))
    entries.extend(find_apis_without_description(surfaces))
    entries.extend(find_models_referenced_but_undocumented(surfaces, beans))
    entries.extend(find_env_vars_not_in_report(surfaces, beans))
    entries.extend(find_auth_checks_without_bean(surfaces, beans))
    entries.extend(find_state_mgmt_without_bean(surfaces, beans))
    entries.extend(find_middleware_without_bean(surfaces, beans))
    entries.extend(find_integrations_without_bean(surfaces, beans))
    entries.extend(find_ui_flows_without_bean(surfaces, beans))
    entries.extend(find_dependencies_without_bean(surfaces, beans))

    logger.info("gap_queries_complete", total_gaps=len(entries))
    return GapReport(entries=entries)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_gaps_markdown(report: GapReport) -> str:
    """Generate human-readable gaps.md content.

    Args:
        report: The gap report with all findings.

    Returns:
        A Markdown string listing all gaps grouped by category.
    """
    lines: list[str] = [
        "# Gap Analysis Report",
        "",
        f"**Total gaps found: {report.total_gaps}**",
        "",
    ]

    if not report.entries:
        lines.append("No gaps found. All coverage gates are satisfied.")
        lines.append("")
        return "\n".join(lines)

    # Group by category
    categories: dict[str, list[GapEntry]] = {}
    for entry in report.entries:
        if entry.category not in categories:
            categories[entry.category] = []
        categories[entry.category].append(entry)

    for category, entries in categories.items():
        lines.append(f"## {category}")
        lines.append("")
        lines.append("| Description | File Path | Recommended Action |")
        lines.append("|---|---|---|")
        for entry in entries:
            lines.append(
                f"| {entry.description} | `{entry.file_path}` | {entry.recommended_action} |"
            )
        lines.append("")

    return "\n".join(lines)


def write_gaps_report(
    output_dir: Path,
    report: GapReport,
) -> Path:
    """Write gaps.md to the reports directory.

    Args:
        output_dir: Root output directory (reports/ subdirectory is created).
        report: The gap report to write.

    Returns:
        Path to the written gaps.md file.
    """
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    md_path = reports_dir / "gaps.md"
    md_content = generate_gaps_markdown(report)
    md_path.write_text(md_content, encoding="utf-8")
    logger.info("gaps_report_written", path=str(md_path))

    return md_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_model_refs(api: ApiSurface) -> set[str]:
    """Extract model name references from an API's schemas.

    Looks for ``$ref`` keys and type names that might reference models.

    Args:
        api: An API surface with request/response schemas.

    Returns:
        Set of model names referenced in the schemas.
    """
    refs: set[str] = set()
    _collect_refs(api.request_schema, refs)
    _collect_refs(api.response_schema, refs)
    return refs


def _collect_refs(schema: dict[str, object], refs: set[str]) -> None:
    """Recursively collect $ref values from a JSON schema-like dict."""
    if not schema:
        return
    for key, value in schema.items():
        if key == "$ref" and isinstance(value, str):
            # Extract model name from ref path like "#/definitions/User"
            name = value.rsplit("/", 1)[-1]
            refs.add(name)
        elif isinstance(value, dict):
            _collect_refs(value, refs)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _collect_refs(item, refs)
