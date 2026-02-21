from __future__ import annotations

from repo_mirror_kit.harvester.analyzers.apis import analyze_api_endpoints
from repo_mirror_kit.harvester.analyzers.auth import analyze_auth
from repo_mirror_kit.harvester.analyzers.build_deploy import analyze_build_deploy
from repo_mirror_kit.harvester.analyzers.components import analyze_components
from repo_mirror_kit.harvester.analyzers.config_env import analyze_config
from repo_mirror_kit.harvester.analyzers.crosscutting import analyze_crosscutting
from repo_mirror_kit.harvester.analyzers.dependencies import analyze_dependencies
from repo_mirror_kit.harvester.analyzers.integrations import analyze_integrations
from repo_mirror_kit.harvester.analyzers.middleware import analyze_middleware
from repo_mirror_kit.harvester.analyzers.models import analyze_models
from repo_mirror_kit.harvester.analyzers.routes import analyze_routes
from repo_mirror_kit.harvester.analyzers.state_mgmt import analyze_state_management
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    BuildDeploySurface,
    ComponentSurface,
    ConfigSurface,
    CrosscuttingSurface,
    DependencySurface,
    IntegrationSurface,
    MiddlewareSurface,
    ModelField,
    ModelSurface,
    RouteSurface,
    SourceRef,
    StateMgmtSurface,
    Surface,
    SurfaceCollection,
    TestPatternSurface,
    UIFlowSurface,
)
from repo_mirror_kit.harvester.analyzers.test_patterns import analyze_test_patterns
from repo_mirror_kit.harvester.analyzers.ui_flows import analyze_ui_flows

__all__ = [
    "ApiSurface",
    "AuthSurface",
    "BuildDeploySurface",
    "ComponentSurface",
    "ConfigSurface",
    "CrosscuttingSurface",
    "DependencySurface",
    "IntegrationSurface",
    "MiddlewareSurface",
    "ModelField",
    "ModelSurface",
    "RouteSurface",
    "SourceRef",
    "StateMgmtSurface",
    "Surface",
    "SurfaceCollection",
    "TestPatternSurface",
    "UIFlowSurface",
    "analyze_api_endpoints",
    "analyze_auth",
    "analyze_build_deploy",
    "analyze_components",
    "analyze_config",
    "analyze_crosscutting",
    "analyze_dependencies",
    "analyze_integrations",
    "analyze_middleware",
    "analyze_models",
    "analyze_routes",
    "analyze_state_management",
    "analyze_test_patterns",
    "analyze_ui_flows",
]
