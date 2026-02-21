"""Build and deploy configuration analyzer.

Detects and extracts metadata from build tooling, CI/CD pipelines,
containerization, infrastructure-as-code, and platform deployment
configs.  Produces ``BuildDeploySurface`` objects for bean generation.

Config categories:
- **container**: Dockerfile, docker-compose.yml, .dockerignore
- **ci_cd**: GitHub Actions, GitLab CI, Jenkins, CircleCI, Azure Pipelines,
  Bitbucket Pipelines
- **build_tool**: Makefile, justfile, taskfile.yml, package.json scripts,
  tox.ini, noxfile.py
- **iac**: Terraform .tf, Pulumi, CloudFormation, Kubernetes manifests
- **platform**: Procfile, app.yaml, fly.toml, render.yaml, vercel.json,
  netlify.toml
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    BuildDeploySurface,
    SourceRef,
)
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

_MAX_FILE_SIZE = 512_000  # Skip files larger than 512 KB


# ---------------------------------------------------------------------------
# File reading helper
# ---------------------------------------------------------------------------


def _read_file_safe(path: Path) -> str | None:
    """Read a file's text content, returning None on failure."""
    try:
        if path.stat().st_size > _MAX_FILE_SIZE:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# File-path matching patterns
# ---------------------------------------------------------------------------

_DOCKERFILE_RE = re.compile(r"(?:^|/)Dockerfile(?:\.\w+)?$")
_COMPOSE_RE = re.compile(r"(?:^|/)(?:docker-)?compose(?:\.\w+)?\.ya?ml$")
_DOCKERIGNORE_RE = re.compile(r"(?:^|/)\.dockerignore$")

_GITHUB_ACTIONS_RE = re.compile(r"(?:^|/)\.github/workflows/.*\.ya?ml$")
_GITLAB_CI_RE = re.compile(r"(?:^|/)\.gitlab-ci\.ya?ml$")
_JENKINSFILE_RE = re.compile(r"(?:^|/)Jenkinsfile$")
_CIRCLECI_RE = re.compile(r"(?:^|/)\.circleci/config\.ya?ml$")
_AZURE_PIPELINES_RE = re.compile(r"(?:^|/)azure-pipelines\.ya?ml$")
_BITBUCKET_PIPELINES_RE = re.compile(r"(?:^|/)bitbucket-pipelines\.ya?ml$")

_MAKEFILE_RE = re.compile(r"(?:^|/)Makefile$")
_JUSTFILE_RE = re.compile(r"(?:^|/)justfile$", re.IGNORECASE)
_TASKFILE_RE = re.compile(r"(?:^|/)(?:Tt)askfile\.ya?ml$")
_PACKAGE_JSON_RE = re.compile(r"(?:^|/)package\.json$")
_TOX_RE = re.compile(r"(?:^|/)tox\.ini$")
_NOXFILE_RE = re.compile(r"(?:^|/)noxfile\.py$")

_TERRAFORM_RE = re.compile(r"(?:^|/).*\.tf$")
_PULUMI_RE = re.compile(r"(?:^|/)Pulumi\.ya?ml$")
_CLOUDFORMATION_RE = re.compile(
    r"(?:^|/)(?:template|cloudformation|cfn).*\.ya?ml$"
    r"|(?:^|/)(?:template|cloudformation|cfn).*\.json$",
    re.IGNORECASE,
)
_K8S_MANIFEST_RE = re.compile(
    r"(?:^|/)(?:k8s|kubernetes|manifests?|deploy)/"
    r".*\.ya?ml$"
)

_PROCFILE_RE = re.compile(r"(?:^|/)Procfile$")
_APP_YAML_RE = re.compile(r"(?:^|/)app\.ya?ml$")
_FLY_TOML_RE = re.compile(r"(?:^|/)fly\.toml$")
_RENDER_YAML_RE = re.compile(r"(?:^|/)render\.ya?ml$")
_VERCEL_JSON_RE = re.compile(r"(?:^|/)vercel\.json$")
_NETLIFY_TOML_RE = re.compile(r"(?:^|/)netlify\.toml$")


# ---------------------------------------------------------------------------
# Content extraction helpers
# ---------------------------------------------------------------------------


def _extract_dockerfile_metadata(content: str) -> dict[str, list[str]]:
    """Extract base images, exposed ports, and build stages from a Dockerfile."""
    base_images: list[str] = []
    ports: list[str] = []
    stages: list[str] = []

    for line in content.splitlines():
        stripped = line.strip()
        from_match = re.match(
            r"^FROM\s+(\S+)(?:\s+AS\s+(\S+))?", stripped, re.IGNORECASE
        )
        if from_match:
            base_images.append(from_match.group(1))
            if from_match.group(2):
                stages.append(from_match.group(2))

        expose_match = re.match(r"^EXPOSE\s+(.+)", stripped, re.IGNORECASE)
        if expose_match:
            ports.extend(expose_match.group(1).split())

    return {
        "base_images": base_images,
        "ports": ports,
        "stages": stages,
    }


def _extract_compose_services(content: str) -> list[str]:
    """Extract service names from a docker-compose file."""
    services: list[str] = []
    in_services = False
    services_indent: int | None = None

    for line in content.splitlines():
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("services:"):
            in_services = True
            services_indent = indent
            continue

        if in_services:
            # A line at the same or less indent level as 'services:' ends the block
            if (
                stripped
                and indent <= (services_indent or 0)
                and not stripped.startswith("#")
            ):
                in_services = False
                continue
            # Service names are one indent level deeper and end with ':'
            if stripped.endswith(":") and not stripped.startswith("#"):
                service_name = stripped.rstrip(":")
                if service_name and " " not in service_name:
                    services.append(service_name)

    return services


def _extract_github_actions_jobs(content: str) -> list[str]:
    """Extract job names from a GitHub Actions workflow file."""
    jobs: list[str] = []
    in_jobs = False
    jobs_indent: int | None = None

    for line in content.splitlines():
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("jobs:"):
            in_jobs = True
            jobs_indent = indent
            continue

        if in_jobs:
            if (
                stripped
                and indent <= (jobs_indent or 0)
                and not stripped.startswith("#")
            ):
                in_jobs = False
                continue
            if stripped.endswith(":") and not stripped.startswith("#"):
                job_name = stripped.rstrip(":")
                if job_name and " " not in job_name:
                    jobs.append(job_name)

    return jobs


def _extract_makefile_targets(content: str) -> list[str]:
    """Extract targets from a Makefile."""
    targets: list[str] = []
    for line in content.splitlines():
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:", line)
        if match:
            target = match.group(1)
            if target not in ("PHONY", "FORCE"):
                targets.append(target)
    return targets


def _extract_justfile_recipes(content: str) -> list[str]:
    """Extract recipe names from a justfile."""
    recipes: list[str] = []
    for line in content.splitlines():
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*(?:\(|:)", line)
        if match:
            recipes.append(match.group(1))
    return recipes


def _extract_package_json_scripts(content: str) -> list[str]:
    """Extract script names from package.json."""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return []
    scripts = data.get("scripts", {})
    if isinstance(scripts, dict):
        return list(scripts.keys())
    return []


def _extract_tox_envs(content: str) -> list[str]:
    """Extract tox environment names from tox.ini."""
    envs: list[str] = []
    for line in content.splitlines():
        match = re.match(r"^\[testenv(?::(\S+))?\]", line)
        if match:
            env_name = match.group(1) or "default"
            envs.append(env_name)
    return envs


def _extract_k8s_kinds(content: str) -> list[str]:
    """Extract Kubernetes resource kinds from a YAML manifest."""
    kinds: list[str] = []
    for match in re.finditer(r"^kind:\s*(\S+)", content, re.MULTILINE):
        kinds.append(match.group(1))
    return kinds


def _extract_terraform_resources(content: str) -> list[str]:
    """Extract resource type names from Terraform .tf files."""
    resources: list[str] = []
    for match in re.finditer(r'^resource\s+"([^"]+)"', content, re.MULTILINE):
        resources.append(match.group(1))
    return resources


def _extract_gitlab_stages(content: str) -> list[str]:
    """Extract stage names from .gitlab-ci.yml."""
    stages: list[str] = []
    in_stages = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "stages:":
            in_stages = True
            continue
        if in_stages:
            if stripped.startswith("- "):
                stages.append(stripped[2:].strip())
            elif stripped and not stripped.startswith("#"):
                break
    return stages


# ---------------------------------------------------------------------------
# Individual extractors
# ---------------------------------------------------------------------------


def _extract_containers(
    inventory: InventoryResult,
    workdir: Path,
) -> list[BuildDeploySurface]:
    """Extract container-related build/deploy surfaces."""
    surfaces: list[BuildDeploySurface] = []

    for entry in inventory.files:
        # Dockerfiles
        if _DOCKERFILE_RE.search(entry.path):
            content = _read_file_safe(workdir / entry.path)
            meta = _extract_dockerfile_metadata(content) if content else {}
            stages = meta.get("stages", [])
            targets = meta.get("base_images", []) + [
                f"port:{p}" for p in meta.get("ports", [])
            ]
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="container",
                    tool="docker",
                    stages=stages,
                    targets=targets,
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

        # docker-compose
        if _COMPOSE_RE.search(entry.path):
            content = _read_file_safe(workdir / entry.path)
            services = _extract_compose_services(content) if content else []
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="container",
                    tool="docker-compose",
                    stages=[],
                    targets=services,
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

        # .dockerignore (presence-only)
        if _DOCKERIGNORE_RE.search(entry.path):
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="container",
                    tool="dockerignore",
                    stages=[],
                    targets=[],
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

    return surfaces


def _extract_ci_cd(
    inventory: InventoryResult,
    workdir: Path,
) -> list[BuildDeploySurface]:
    """Extract CI/CD pipeline surfaces."""
    surfaces: list[BuildDeploySurface] = []

    for entry in inventory.files:
        # GitHub Actions
        if _GITHUB_ACTIONS_RE.search(entry.path):
            content = _read_file_safe(workdir / entry.path)
            jobs = _extract_github_actions_jobs(content) if content else []
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="ci_cd",
                    tool="github-actions",
                    stages=jobs,
                    targets=[],
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

        # GitLab CI
        if _GITLAB_CI_RE.search(entry.path):
            content = _read_file_safe(workdir / entry.path)
            stages = _extract_gitlab_stages(content) if content else []
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="ci_cd",
                    tool="gitlab-ci",
                    stages=stages,
                    targets=[],
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

        # Jenkinsfile
        if _JENKINSFILE_RE.search(entry.path):
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="ci_cd",
                    tool="jenkins",
                    stages=[],
                    targets=[],
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

        # CircleCI
        if _CIRCLECI_RE.search(entry.path):
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="ci_cd",
                    tool="circleci",
                    stages=[],
                    targets=[],
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

        # Azure Pipelines
        if _AZURE_PIPELINES_RE.search(entry.path):
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="ci_cd",
                    tool="azure-pipelines",
                    stages=[],
                    targets=[],
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

        # Bitbucket Pipelines
        if _BITBUCKET_PIPELINES_RE.search(entry.path):
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="ci_cd",
                    tool="bitbucket-pipelines",
                    stages=[],
                    targets=[],
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

    return surfaces


def _extract_build_tools(
    inventory: InventoryResult,
    workdir: Path,
) -> list[BuildDeploySurface]:
    """Extract build tool surfaces."""
    surfaces: list[BuildDeploySurface] = []

    for entry in inventory.files:
        # Makefile
        if _MAKEFILE_RE.search(entry.path):
            content = _read_file_safe(workdir / entry.path)
            targets = _extract_makefile_targets(content) if content else []
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="build_tool",
                    tool="make",
                    stages=[],
                    targets=targets,
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

        # justfile
        if _JUSTFILE_RE.search(entry.path):
            content = _read_file_safe(workdir / entry.path)
            recipes = _extract_justfile_recipes(content) if content else []
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="build_tool",
                    tool="just",
                    stages=[],
                    targets=recipes,
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

        # taskfile.yml
        if _TASKFILE_RE.search(entry.path):
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="build_tool",
                    tool="task",
                    stages=[],
                    targets=[],
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

        # package.json (scripts section)
        if _PACKAGE_JSON_RE.search(entry.path):
            content = _read_file_safe(workdir / entry.path)
            scripts = _extract_package_json_scripts(content) if content else []
            if scripts:
                surfaces.append(
                    BuildDeploySurface(
                        name=entry.path,
                        config_type="build_tool",
                        tool="npm-scripts",
                        stages=[],
                        targets=scripts,
                        source_refs=[SourceRef(file_path=entry.path)],
                    )
                )

        # tox.ini
        if _TOX_RE.search(entry.path):
            content = _read_file_safe(workdir / entry.path)
            envs = _extract_tox_envs(content) if content else []
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="build_tool",
                    tool="tox",
                    stages=[],
                    targets=envs,
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

        # noxfile.py
        if _NOXFILE_RE.search(entry.path):
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="build_tool",
                    tool="nox",
                    stages=[],
                    targets=[],
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

    return surfaces


def _extract_iac(
    inventory: InventoryResult,
    workdir: Path,
) -> list[BuildDeploySurface]:
    """Extract infrastructure-as-code surfaces."""
    surfaces: list[BuildDeploySurface] = []

    # Collect terraform files by directory
    tf_dirs: dict[str, list[str]] = {}
    for entry in inventory.files:
        if _TERRAFORM_RE.search(entry.path):
            tf_dir = str(Path(entry.path).parent)
            if tf_dir not in tf_dirs:
                tf_dirs[tf_dir] = []
            tf_dirs[tf_dir].append(entry.path)

    for tf_dir, tf_files in tf_dirs.items():
        all_resources: list[str] = []
        refs: list[SourceRef] = []
        for fp in tf_files:
            content = _read_file_safe(workdir / fp)
            if content:
                all_resources.extend(_extract_terraform_resources(content))
            refs.append(SourceRef(file_path=fp))
        surfaces.append(
            BuildDeploySurface(
                name=f"terraform:{tf_dir}",
                config_type="iac",
                tool="terraform",
                stages=[],
                targets=all_resources,
                source_refs=refs,
            )
        )

    for entry in inventory.files:
        # Pulumi
        if _PULUMI_RE.search(entry.path):
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="iac",
                    tool="pulumi",
                    stages=[],
                    targets=[],
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

        # Kubernetes manifests
        if _K8S_MANIFEST_RE.search(entry.path):
            content = _read_file_safe(workdir / entry.path)
            kinds = _extract_k8s_kinds(content) if content else []
            surfaces.append(
                BuildDeploySurface(
                    name=entry.path,
                    config_type="iac",
                    tool="kubernetes",
                    stages=[],
                    targets=kinds,
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )

    return surfaces


def _extract_platform_configs(
    inventory: InventoryResult,
    workdir: Path,
) -> list[BuildDeploySurface]:
    """Extract platform deployment config surfaces."""
    surfaces: list[BuildDeploySurface] = []

    _platform_patterns: list[tuple[str, re.Pattern[str]]] = [
        ("heroku", _PROCFILE_RE),
        ("app-engine", _APP_YAML_RE),
        ("fly", _FLY_TOML_RE),
        ("render", _RENDER_YAML_RE),
        ("vercel", _VERCEL_JSON_RE),
        ("netlify", _NETLIFY_TOML_RE),
    ]

    for entry in inventory.files:
        for tool, pattern_re in _platform_patterns:
            if pattern_re.search(entry.path):
                surfaces.append(
                    BuildDeploySurface(
                        name=entry.path,
                        config_type="platform",
                        tool=tool,
                        stages=[],
                        targets=[],
                        source_refs=[SourceRef(file_path=entry.path)],
                    )
                )

    return surfaces


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_build_deploy(
    inventory: InventoryResult,
    workdir: Path,
) -> list[BuildDeploySurface]:
    """Analyze repository files for build and deploy configuration.

    Scans the file inventory for containerization, CI/CD, build tools,
    infrastructure-as-code, and platform deployment configs.

    Args:
        inventory: The scanned file inventory.
        workdir: Root directory of the repository checkout.

    Returns:
        A list of BuildDeploySurface objects for all detected configs.
    """
    surfaces: list[BuildDeploySurface] = []

    extractors = [
        ("container", _extract_containers),
        ("ci_cd", _extract_ci_cd),
        ("build_tool", _extract_build_tools),
        ("iac", _extract_iac),
        ("platform", _extract_platform_configs),
    ]

    for category, extractor in extractors:
        logger.info("build_deploy_analysis_starting", category=category)
        results = extractor(inventory, workdir)
        surfaces.extend(results)
        logger.info(
            "build_deploy_analysis_complete",
            category=category,
            surfaces_found=len(results),
        )

    logger.info("build_deploy_analysis_total", total_surfaces=len(surfaces))
    return surfaces
