"""Surface data model for the harvester analyzers.

Defines typed dataclasses representing each surface type extracted from code:
routes, components, APIs, models, auth rules, config, and cross-cutting concerns.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceRef:
    """A reference to a location in source code."""

    file_path: str
    start_line: int | None = None
    end_line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
        }


@dataclass
class Surface:
    """Base class for all surface types.

    Every surface has a name, a type discriminator, one or more
    references to the source code locations where it was found,
    and an optional enrichment dict populated by LLM analysis.
    """

    name: str
    surface_type: str = ""
    source_refs: list[SourceRef] = field(default_factory=list)
    enrichment: dict[str, Any] = field(default_factory=dict)
    # Keys when populated: behavioral_description, inferred_intent,
    # given_when_then (list of {given, when, then}), data_flow, priority, dependencies

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result: dict[str, Any] = {
            "name": self.name,
            "surface_type": self.surface_type,
            "source_refs": [ref.to_dict() for ref in self.source_refs],
        }
        if self.enrichment:
            result["enrichment"] = self.enrichment
        return result


@dataclass
class RouteSurface(Surface):
    """A route surface extracted from routing definitions."""

    path: str = ""
    method: str = ""
    component_refs: list[str] = field(default_factory=list)
    api_refs: list[str] = field(default_factory=list)
    auth_requirements: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "route"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "path": self.path,
                "method": self.method,
                "component_refs": self.component_refs,
                "api_refs": self.api_refs,
                "auth_requirements": self.auth_requirements,
            }
        )
        return result


@dataclass
class ComponentSurface(Surface):
    """A UI component surface."""

    props: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    usage_locations: list[str] = field(default_factory=list)
    states: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "component"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "props": self.props,
                "outputs": self.outputs,
                "usage_locations": self.usage_locations,
                "states": self.states,
            }
        )
        return result


@dataclass
class ApiSurface(Surface):
    """An API endpoint surface."""

    method: str = ""
    path: str = ""
    auth: str = ""
    request_schema: dict[str, Any] = field(default_factory=dict)
    response_schema: dict[str, Any] = field(default_factory=dict)
    side_effects: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "api"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "method": self.method,
                "path": self.path,
                "auth": self.auth,
                "request_schema": self.request_schema,
                "response_schema": self.response_schema,
                "side_effects": self.side_effects,
            }
        )
        return result


@dataclass(frozen=True)
class ModelField:
    """A field within a model surface."""

    name: str
    field_type: str
    constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "field_type": self.field_type,
            "constraints": self.constraints,
        }


@dataclass
class ModelSurface(Surface):
    """A data model / entity surface."""

    entity_name: str = ""
    fields: list[ModelField] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    persistence_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "model"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "entity_name": self.entity_name,
                "fields": [f.to_dict() for f in self.fields],
                "relationships": self.relationships,
                "persistence_refs": self.persistence_refs,
            }
        )
        return result


@dataclass
class AuthSurface(Surface):
    """An authentication/authorization surface."""

    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    protected_endpoints: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "auth"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "roles": self.roles,
                "permissions": self.permissions,
                "rules": self.rules,
                "protected_endpoints": self.protected_endpoints,
            }
        )
        return result


@dataclass
class ConfigSurface(Surface):
    """A configuration / environment variable surface."""

    env_var_name: str = ""
    default_value: str | None = None
    required: bool = False
    usage_locations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "config"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "env_var_name": self.env_var_name,
                "default_value": self.default_value,
                "required": self.required,
                "usage_locations": self.usage_locations,
            }
        )
        return result


@dataclass
class CrosscuttingSurface(Surface):
    """A cross-cutting concern surface (logging, error handling, etc.)."""

    concern_type: str = ""
    description: str = ""
    affected_files: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "crosscutting"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "concern_type": self.concern_type,
                "description": self.description,
                "affected_files": self.affected_files,
            }
        )
        return result


@dataclass
class StateMgmtSurface(Surface):
    """A state management surface (Redux, Zustand, Context, etc.)."""

    store_name: str = ""
    pattern: str = ""  # redux/vuex/zustand/pinia/context/signals
    actions: list[str] = field(default_factory=list)
    selectors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "state_mgmt"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "store_name": self.store_name,
                "pattern": self.pattern,
                "actions": self.actions,
                "selectors": self.selectors,
            }
        )
        return result


@dataclass
class MiddlewareSurface(Surface):
    """A middleware / pipeline surface."""

    middleware_type: str = ""
    execution_order: int | None = None
    applies_to: list[str] = field(default_factory=list)
    transforms: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "middleware"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "middleware_type": self.middleware_type,
                "execution_order": self.execution_order,
                "applies_to": self.applies_to,
                "transforms": self.transforms,
            }
        )
        return result


@dataclass
class IntegrationSurface(Surface):
    """An external integration surface (webhook, queue, gRPC, etc.)."""

    integration_type: str = ""  # webhook/queue/grpc/rest_client/sdk
    target_service: str = ""
    protocol: str = ""
    data_exchanged: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "integration"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "integration_type": self.integration_type,
                "target_service": self.target_service,
                "protocol": self.protocol,
                "data_exchanged": self.data_exchanged,
            }
        )
        return result


@dataclass
class UIFlowSurface(Surface):
    """A UI interaction flow surface (wizard, navigation, modal chain, etc.)."""

    flow_type: str = ""  # wizard/navigation/modal_chain/form_sequence
    steps: list[str] = field(default_factory=list)
    entry_point: str = ""
    exit_points: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "ui_flow"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "flow_type": self.flow_type,
                "steps": self.steps,
                "entry_point": self.entry_point,
                "exit_points": self.exit_points,
            }
        )
        return result


@dataclass
class BuildDeploySurface(Surface):
    """A build/deploy configuration surface."""

    config_type: str = ""  # container/ci_cd/build_tool/iac/platform
    tool: str = ""
    stages: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "build_deploy"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "config_type": self.config_type,
                "tool": self.tool,
                "stages": self.stages,
                "targets": self.targets,
            }
        )
        return result


@dataclass
class DependencySurface(Surface):
    """A dependency / package surface extracted from manifest files."""

    version_constraint: str = ""
    purpose: str = ""  # runtime/dev/test/build/peer
    manifest_file: str = ""
    is_direct: bool = True
    lock_files: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.surface_type = "dependency"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result = super().to_dict()
        result.update(
            {
                "version_constraint": self.version_constraint,
                "purpose": self.purpose,
                "manifest_file": self.manifest_file,
                "is_direct": self.is_direct,
                "lock_files": self.lock_files,
            }
        )
        return result


@dataclass
class SurfaceCollection:
    """Container for all extracted surfaces.

    Holds typed lists for each surface category and supports
    iteration over all surfaces regardless of type.
    """

    routes: list[RouteSurface] = field(default_factory=list)
    components: list[ComponentSurface] = field(default_factory=list)
    apis: list[ApiSurface] = field(default_factory=list)
    models: list[ModelSurface] = field(default_factory=list)
    auth: list[AuthSurface] = field(default_factory=list)
    config: list[ConfigSurface] = field(default_factory=list)
    crosscutting: list[CrosscuttingSurface] = field(default_factory=list)
    state_mgmt: list[StateMgmtSurface] = field(default_factory=list)
    middleware: list[MiddlewareSurface] = field(default_factory=list)
    integrations: list[IntegrationSurface] = field(default_factory=list)
    ui_flows: list[UIFlowSurface] = field(default_factory=list)
    build_deploy: list[BuildDeploySurface] = field(default_factory=list)
    dependencies: list[DependencySurface] = field(default_factory=list)

    def __iter__(self) -> Iterator[Surface]:
        """Iterate over all surfaces in the collection."""
        yield from self.routes
        yield from self.components
        yield from self.apis
        yield from self.models
        yield from self.auth
        yield from self.config
        yield from self.crosscutting
        yield from self.state_mgmt
        yield from self.middleware
        yield from self.integrations
        yield from self.ui_flows
        yield from self.build_deploy
        yield from self.dependencies

    def __len__(self) -> int:
        """Return the total number of surfaces."""
        return (
            len(self.routes)
            + len(self.components)
            + len(self.apis)
            + len(self.models)
            + len(self.auth)
            + len(self.config)
            + len(self.crosscutting)
            + len(self.state_mgmt)
            + len(self.middleware)
            + len(self.integrations)
            + len(self.ui_flows)
            + len(self.build_deploy)
            + len(self.dependencies)
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire collection to a JSON-compatible dictionary."""
        return {
            "routes": [s.to_dict() for s in self.routes],
            "components": [s.to_dict() for s in self.components],
            "apis": [s.to_dict() for s in self.apis],
            "models": [s.to_dict() for s in self.models],
            "auth": [s.to_dict() for s in self.auth],
            "config": [s.to_dict() for s in self.config],
            "crosscutting": [s.to_dict() for s in self.crosscutting],
            "state_mgmt": [s.to_dict() for s in self.state_mgmt],
            "middleware": [s.to_dict() for s in self.middleware],
            "integrations": [s.to_dict() for s in self.integrations],
            "ui_flows": [s.to_dict() for s in self.ui_flows],
            "build_deploy": [s.to_dict() for s in self.build_deploy],
            "dependencies": [s.to_dict() for s in self.dependencies],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize the collection to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
