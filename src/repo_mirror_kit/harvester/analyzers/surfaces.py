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

    Every surface has a name, a type discriminator, and one or more
    references to the source code locations where it was found.
    """

    name: str
    surface_type: str = ""
    source_refs: list[SourceRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "surface_type": self.surface_type,
            "source_refs": [ref.to_dict() for ref in self.source_refs],
        }


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

    def __iter__(self) -> Iterator[Surface]:
        """Iterate over all surfaces in the collection."""
        yield from self.routes
        yield from self.components
        yield from self.apis
        yield from self.models
        yield from self.auth
        yield from self.config
        yield from self.crosscutting

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
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize the collection to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
