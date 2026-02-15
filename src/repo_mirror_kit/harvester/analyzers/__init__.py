from __future__ import annotations

from repo_mirror_kit.harvester.analyzers.apis import analyze_api_endpoints
from repo_mirror_kit.harvester.analyzers.auth import analyze_auth
from repo_mirror_kit.harvester.analyzers.components import analyze_components
from repo_mirror_kit.harvester.analyzers.config_env import analyze_config
from repo_mirror_kit.harvester.analyzers.crosscutting import analyze_crosscutting
from repo_mirror_kit.harvester.analyzers.models import analyze_models
from repo_mirror_kit.harvester.analyzers.routes import analyze_routes
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    ComponentSurface,
    ConfigSurface,
    CrosscuttingSurface,
    ModelField,
    ModelSurface,
    RouteSurface,
    SourceRef,
    Surface,
    SurfaceCollection,
)

__all__ = [
    "ApiSurface",
    "AuthSurface",
    "ComponentSurface",
    "ConfigSurface",
    "CrosscuttingSurface",
    "ModelField",
    "ModelSurface",
    "RouteSurface",
    "SourceRef",
    "Surface",
    "SurfaceCollection",
    "analyze_api_endpoints",
    "analyze_auth",
    "analyze_components",
    "analyze_config",
    "analyze_crosscutting",
    "analyze_models",
    "analyze_routes",
]
