from __future__ import annotations

from repo_mirror_kit.harvester.analyzers.api_contracts import (
    populate_python_api_contracts,
)
from repo_mirror_kit.harvester.analyzers.api_contracts_dotnet import (
    populate_dotnet_api_contracts,
)
from repo_mirror_kit.harvester.analyzers.api_contracts_js import (
    populate_js_api_contracts,
)
from repo_mirror_kit.harvester.analyzers.apis import analyze_api_endpoints
from repo_mirror_kit.harvester.analyzers.auth import analyze_auth
from repo_mirror_kit.harvester.analyzers.behavioral_spec import analyze_behavioral_spec
from repo_mirror_kit.harvester.analyzers.build_deploy import analyze_build_deploy
from repo_mirror_kit.harvester.analyzers.business_rules import analyze_business_rules
from repo_mirror_kit.harvester.analyzers.components import analyze_components
from repo_mirror_kit.harvester.analyzers.config_env import analyze_config
from repo_mirror_kit.harvester.analyzers.crosscutting import analyze_crosscutting
from repo_mirror_kit.harvester.analyzers.dependencies import analyze_dependencies
from repo_mirror_kit.harvester.analyzers.file_coverage import (
    analyze_uncovered_files,
    find_uncovered_files,
)
from repo_mirror_kit.harvester.analyzers.integrations import analyze_integrations
from repo_mirror_kit.harvester.analyzers.middleware import analyze_middleware
from repo_mirror_kit.harvester.analyzers.models import analyze_models
from repo_mirror_kit.harvester.analyzers.routes import analyze_routes
from repo_mirror_kit.harvester.analyzers.screens import analyze_screens
from repo_mirror_kit.harvester.analyzers.seed_data import analyze_seed_data
from repo_mirror_kit.harvester.analyzers.state_mgmt import analyze_state_management
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
from repo_mirror_kit.harvester.analyzers.test_patterns import analyze_test_patterns
from repo_mirror_kit.harvester.analyzers.ui_flows import analyze_ui_flows
from repo_mirror_kit.harvester.analyzers.workflows import analyze_workflows

__all__ = [
    "ApiSurface",
    "AuthSurface",
    "BuildDeploySurface",
    "BusinessRuleSurface",
    "ComponentSurface",
    "ConfigSurface",
    "CrosscuttingSurface",
    "DependencySurface",
    "GeneralLogicSurface",
    "IntegrationSurface",
    "MiddlewareSurface",
    "ModelField",
    "ModelRelationship",
    "ModelSurface",
    "RouteSurface",
    "ScreenAction",
    "ScreenField",
    "ScreenSurface",
    "SeedDataSurface",
    "SourceRef",
    "StateMgmtSurface",
    "Surface",
    "SurfaceCollection",
    "TestPatternSurface",
    "UIFlowSurface",
    "WorkflowSurface",
    "WorkflowTransition",
    "analyze_api_endpoints",
    "analyze_auth",
    "analyze_behavioral_spec",
    "analyze_build_deploy",
    "analyze_business_rules",
    "analyze_components",
    "analyze_config",
    "analyze_crosscutting",
    "analyze_dependencies",
    "analyze_integrations",
    "analyze_middleware",
    "analyze_models",
    "analyze_routes",
    "analyze_screens",
    "analyze_seed_data",
    "analyze_state_management",
    "analyze_test_patterns",
    "analyze_ui_flows",
    "analyze_uncovered_files",
    "analyze_workflows",
    "find_uncovered_files",
    "populate_dotnet_api_contracts",
    "populate_js_api_contracts",
    "populate_python_api_contracts",
]
