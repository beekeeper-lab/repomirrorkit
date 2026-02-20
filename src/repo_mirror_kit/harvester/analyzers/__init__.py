from __future__ import annotations

from repo_mirror_kit.harvester.analyzers.apis import analyze_api_endpoints
from repo_mirror_kit.harvester.analyzers.auth import analyze_auth
from repo_mirror_kit.harvester.analyzers.components import analyze_components
from repo_mirror_kit.harvester.analyzers.config_env import analyze_config
from repo_mirror_kit.harvester.analyzers.crosscutting import analyze_crosscutting
from repo_mirror_kit.harvester.analyzers.integrations import analyze_integrations
from repo_mirror_kit.harvester.analyzers.middleware import analyze_middleware
from repo_mirror_kit.harvester.analyzers.models import analyze_models
from repo_mirror_kit.harvester.analyzers.routes import analyze_routes
from repo_mirror_kit.harvester.analyzers.state_mgmt import analyze_state_management
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    ComponentSurface,
    ConfigSurface,
    CrosscuttingSurface,
    IntegrationSurface,
    MiddlewareSurface,
    ModelField,
    ModelSurface,
    RouteSurface,
    SourceRef,
    StateMgmtSurface,
    Surface,
    SurfaceCollection,
    UIFlowSurface,
)
from repo_mirror_kit.harvester.analyzers.ui_flows import analyze_ui_flows

__all__ = [
    "ApiSurface",
    "AuthSurface",
    "ComponentSurface",
    "ConfigSurface",
    "CrosscuttingSurface",
    "IntegrationSurface",
    "MiddlewareSurface",
    "ModelField",
    "ModelSurface",
    "RouteSurface",
    "SourceRef",
    "StateMgmtSurface",
    "Surface",
    "SurfaceCollection",
    "UIFlowSurface",
    "analyze_api_endpoints",
    "analyze_auth",
    "analyze_components",
    "analyze_config",
    "analyze_crosscutting",
    "analyze_integrations",
    "analyze_middleware",
    "analyze_models",
    "analyze_routes",
    "analyze_state_management",
    "analyze_ui_flows",
]
