"""Stage-output persistence and rehydration (BEAN-060).

Serializes the expensive intermediate results of pipeline stages B, C,
and C2 to ``<out>/state/`` so ``--resume`` can rehydrate them instead of
re-running the work — critical once LLM enrichment (stage C2) carries a
real cost per run.

Layout under ``<out>/state/``::

    inventory.json          Stage B: file inventory
    profile.json            Stage B: stack detection profile
    surfaces.json           Stage C: extracted surfaces
    surfaces-enriched.json  Stage C2: surfaces after LLM enrichment

Each artifact is guarded by a SHA-256 recorded in ``state.json``
(see :class:`~repo_mirror_kit.harvester.state.StateManager`): rehydration
happens only when the file on disk still matches the hash recorded when
the stage completed, so a corrupted or hand-edited artifact triggers a
re-run instead of poisoning the pipeline.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    BuildDeploySurface,
    BusinessRuleSurface,
    ComponentSurface,
    ConfigSurface,
    CrosscuttingSurface,
    DependencySurface,
    GeneralLogicSurface,
    IntegrationSurface,
    MiddlewareSurface,
    ModelField,
    ModelRelationship,
    ModelSurface,
    RouteSurface,
    ScreenAction,
    ScreenField,
    ScreenSurface,
    SeedDataSurface,
    SourceRef,
    StateMgmtSurface,
    Surface,
    SurfaceCollection,
    TestPatternSurface,
    UIFlowSurface,
    WorkflowSurface,
    WorkflowTransition,
)
from repo_mirror_kit.harvester.detectors.base import Signal, StackProfile
from repo_mirror_kit.harvester.inventory import (
    FileEntry,
    InventoryResult,
    SkippedFile,
)

logger = structlog.get_logger()

INVENTORY_ARTIFACT = "inventory.json"
PROFILE_ARTIFACT = "profile.json"
SURFACES_ARTIFACT = "surfaces.json"
ENRICHED_SURFACES_ARTIFACT = "surfaces-enriched.json"

# surface_type discriminator → concrete class. Types with nested
# structures get dedicated field decoding below.
_SURFACE_TYPES: dict[str, type[Surface]] = {
    "route": RouteSurface,
    "component": ComponentSurface,
    "api": ApiSurface,
    "model": ModelSurface,
    "auth": AuthSurface,
    "config": ConfigSurface,
    "crosscutting": CrosscuttingSurface,
    "state_mgmt": StateMgmtSurface,
    "middleware": MiddlewareSurface,
    "integration": IntegrationSurface,
    "ui_flow": UIFlowSurface,
    "build_deploy": BuildDeploySurface,
    "dependency": DependencySurface,
    "test_pattern": TestPatternSurface,
    "seed_data": SeedDataSurface,
    "screen": ScreenSurface,
    "business_rule": BusinessRuleSurface,
    "workflow": WorkflowSurface,
    "general_logic": GeneralLogicSurface,
}

# SurfaceCollection attribute → surface_type key in to_dict() output.
_COLLECTION_FIELDS: dict[str, str] = {
    "routes": "route",
    "components": "component",
    "apis": "api",
    "models": "model",
    "auth": "auth",
    "config": "config",
    "crosscutting": "crosscutting",
    "state_mgmt": "state_mgmt",
    "middleware": "middleware",
    "integrations": "integration",
    "ui_flows": "ui_flow",
    "build_deploy": "build_deploy",
    "dependencies": "dependency",
    "test_patterns": "test_pattern",
    "seed_data": "seed_data",
    "screens": "screen",
    "business_rules": "business_rule",
    "workflows": "workflow",
    "general_logic": "general_logic",
}

# Base-class keys handled explicitly rather than passed as kwargs.
_BASE_KEYS = frozenset({"name", "surface_type", "source_refs", "enrichment"})


def sha256_of(path: Path) -> str:
    """Hex SHA-256 of a file's contents."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_ref_from_dict(data: dict[str, Any]) -> SourceRef:
    return SourceRef(
        file_path=data.get("file_path", ""),
        start_line=data.get("start_line"),
        end_line=data.get("end_line"),
    )


def surface_from_dict(data: dict[str, Any]) -> Surface:
    """Reconstruct a concrete Surface from its ``to_dict()`` output.

    Raises:
        ValueError: If the surface_type discriminator is unknown.
    """
    surface_type = data.get("surface_type", "")
    cls = _SURFACE_TYPES.get(surface_type)
    if cls is None:
        msg = f"Unknown surface_type in persisted data: {surface_type!r}"
        raise ValueError(msg)

    kwargs: dict[str, Any] = {}
    known_fields = {f for f in cls.__dataclass_fields__ if f not in _BASE_KEYS}
    for key, value in data.items():
        if key in _BASE_KEYS or key not in known_fields:
            continue
        kwargs[key] = value

    # Nested structures that to_dict() flattened.
    if cls is ModelSurface:
        kwargs["fields"] = [
            ModelField(
                name=f.get("name", ""),
                field_type=f.get("field_type", ""),
                constraints=list(f.get("constraints", [])),
            )
            for f in data.get("fields", [])
        ]
        kwargs["relationship_details"] = [
            ModelRelationship(
                source_model=r.get("source_model", ""),
                target_model=r.get("target_model", ""),
                kind=r.get("kind", ""),
                fk_column=r.get("fk_column"),
                cascade=r.get("cascade"),
                source_file=r.get("source_file"),
            )
            for r in data.get("relationship_details", [])
        ]

    if cls is ScreenSurface:
        kwargs["fields"] = [
            ScreenField(
                **{k: v for k, v in f.items() if k in ScreenField.__dataclass_fields__}
            )
            for f in data.get("fields", [])
        ]
        kwargs["actions"] = [
            ScreenAction(
                **{k: v for k, v in a.items() if k in ScreenAction.__dataclass_fields__}
            )
            for a in data.get("actions", [])
        ]

    if cls is WorkflowSurface:
        kwargs["transitions"] = [
            WorkflowTransition(
                **{
                    k: v
                    for k, v in t.items()
                    if k in WorkflowTransition.__dataclass_fields__
                }
            )
            for t in data.get("transitions", [])
        ]

    surface = cls(
        name=data.get("name", ""),
        source_refs=[_source_ref_from_dict(r) for r in data.get("source_refs", [])],
        enrichment=dict(data.get("enrichment", {})),
        **kwargs,
    )
    return surface


def surface_collection_from_dict(data: dict[str, Any]) -> SurfaceCollection:
    """Reconstruct a SurfaceCollection from its ``to_dict()`` output."""
    collection = SurfaceCollection()
    for attr in _COLLECTION_FIELDS:
        entries = data.get(attr, [])
        rebuilt = [surface_from_dict(entry) for entry in entries]
        setattr(collection, attr, rebuilt)
    return collection


def inventory_to_dict(inventory: InventoryResult) -> dict[str, Any]:
    """Serialize an InventoryResult (including workdir) for persistence."""
    return {
        "files": [
            {
                "path": f.path,
                "size": f.size,
                "extension": f.extension,
                "hash": f.hash,
                "category": f.category,
            }
            for f in inventory.files
        ],
        "skipped": [
            {"path": s.path, "reason": s.reason, "size": s.size}
            for s in inventory.skipped
        ],
        "total_files": inventory.total_files,
        "total_size": inventory.total_size,
        "total_skipped": inventory.total_skipped,
        "workdir": str(inventory.workdir) if inventory.workdir else None,
    }


def inventory_from_dict(data: dict[str, Any]) -> InventoryResult:
    """Reconstruct an InventoryResult from persisted data."""
    return InventoryResult(
        files=[
            FileEntry(
                path=f["path"],
                size=f["size"],
                extension=f["extension"],
                hash=f["hash"],
                category=f["category"],
            )
            for f in data.get("files", [])
        ],
        skipped=[
            SkippedFile(path=s["path"], reason=s["reason"], size=s.get("size"))
            for s in data.get("skipped", [])
        ],
        total_files=data.get("total_files", 0),
        total_size=data.get("total_size", 0),
        total_skipped=data.get("total_skipped", 0),
        workdir=Path(data["workdir"]) if data.get("workdir") else None,
    )


def profile_to_dict(profile: StackProfile) -> dict[str, Any]:
    """Serialize a StackProfile for persistence."""
    return {
        "stacks": profile.stacks,
        "evidence": profile.evidence,
        "signals": [
            {
                "stack_name": s.stack_name,
                "confidence": s.confidence,
                "evidence": s.evidence,
            }
            for s in profile.signals
        ],
    }


def profile_from_dict(data: dict[str, Any]) -> StackProfile:
    """Reconstruct a StackProfile from persisted data."""
    return StackProfile(
        stacks=dict(data.get("stacks", {})),
        evidence={k: list(v) for k, v in data.get("evidence", {}).items()},
        signals=[
            Signal(
                stack_name=s["stack_name"],
                confidence=s["confidence"],
                evidence=list(s.get("evidence", [])),
            )
            for s in data.get("signals", [])
        ],
    )


def write_artifact(state_dir: Path, filename: str, data: dict[str, Any]) -> str:
    """Write a JSON artifact under the state directory; return its SHA-256."""
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / filename
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    digest = sha256_of(path)
    logger.info("stage_artifact_written", path=str(path), sha256=digest[:12])
    return digest


def read_artifact(
    state_dir: Path, filename: str, expected_sha256: str | None
) -> dict[str, Any] | None:
    """Read a JSON artifact if present and hash-intact; None otherwise."""
    path = state_dir / filename
    if not path.is_file():
        return None
    if expected_sha256 is not None and sha256_of(path) != expected_sha256:
        logger.warning(
            "stage_artifact_hash_mismatch",
            path=str(path),
            msg="artifact changed since it was recorded; stage will re-run",
        )
        return None
    try:
        loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("stage_artifact_unreadable", path=str(path))
        return None
    return loaded
