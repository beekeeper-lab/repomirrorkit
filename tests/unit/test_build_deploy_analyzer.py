"""Unit tests for the build and deploy configuration analyzer."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.build_deploy import analyze_build_deploy
from repo_mirror_kit.harvester.analyzers.surfaces import BuildDeploySurface
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory(paths: list[str]) -> InventoryResult:
    """Build an InventoryResult from a list of file paths."""
    files = [
        FileEntry(
            path=p,
            size=100,
            extension="." + p.rsplit(".", 1)[-1] if "." in p else "",
            hash="abc123",
            category="source",
        )
        for p in paths
    ]
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=len(files) * 100,
        total_skipped=0,
    )


def _write_file(workdir: Path, rel_path: str, content: str) -> None:
    """Write a file under workdir with the given content."""
    full = workdir / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(textwrap.dedent(content), encoding="utf-8")


# ---------------------------------------------------------------------------
# Empty / no-match
# ---------------------------------------------------------------------------


class TestEmptyRepository:
    """Analyzer returns empty when no build/deploy configs found."""

    def test_empty_inventory(self, tmp_path: Path) -> None:
        inventory = _make_inventory([])
        result = analyze_build_deploy(inventory, tmp_path)
        assert result == []

    def test_unrelated_files(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "src/main.py", "print('hello')\n")
        inventory = _make_inventory(["src/main.py"])
        result = analyze_build_deploy(inventory, tmp_path)
        assert result == []


# ---------------------------------------------------------------------------
# Dockerfile detection
# ---------------------------------------------------------------------------


class TestDockerfileDetection:
    """Detect Dockerfiles and extract metadata."""

    def test_basic_dockerfile(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Dockerfile",
            """\
            FROM python:3.12-slim
            EXPOSE 8000
            CMD ["python", "app.py"]
            """,
        )
        inventory = _make_inventory(["Dockerfile"])
        result = analyze_build_deploy(inventory, tmp_path)

        assert len(result) >= 1
        docker_surfaces = [s for s in result if s.tool == "docker"]
        assert len(docker_surfaces) == 1
        assert docker_surfaces[0].config_type == "container"
        assert "python:3.12-slim" in docker_surfaces[0].targets
        assert "port:8000" in docker_surfaces[0].targets

    def test_multistage_dockerfile(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Dockerfile",
            """\
            FROM node:18 AS builder
            RUN npm ci
            FROM node:18-slim AS runtime
            EXPOSE 3000
            """,
        )
        inventory = _make_inventory(["Dockerfile"])
        result = analyze_build_deploy(inventory, tmp_path)

        docker_surfaces = [s for s in result if s.tool == "docker"]
        assert len(docker_surfaces) == 1
        assert "builder" in docker_surfaces[0].stages
        assert "runtime" in docker_surfaces[0].stages
        assert "node:18" in docker_surfaces[0].targets
        assert "node:18-slim" in docker_surfaces[0].targets


# ---------------------------------------------------------------------------
# docker-compose detection
# ---------------------------------------------------------------------------


class TestDockerComposeDetection:
    """Detect docker-compose files and extract service definitions."""

    def test_basic_compose(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "docker-compose.yml",
            """\
            version: "3.8"
            services:
              web:
                build: .
                ports:
                  - "8000:8000"
              db:
                image: postgres:15
            """,
        )
        inventory = _make_inventory(["docker-compose.yml"])
        result = analyze_build_deploy(inventory, tmp_path)

        compose_surfaces = [s for s in result if s.tool == "docker-compose"]
        assert len(compose_surfaces) == 1
        assert "web" in compose_surfaces[0].targets
        assert "db" in compose_surfaces[0].targets


# ---------------------------------------------------------------------------
# GitHub Actions detection
# ---------------------------------------------------------------------------


class TestGitHubActionsDetection:
    """Detect GitHub Actions workflows and extract job names."""

    def test_github_actions_workflow(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".github/workflows/ci.yml",
            """\
            name: CI
            on: push
            jobs:
              lint:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4
              test:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4
            """,
        )
        inventory = _make_inventory([".github/workflows/ci.yml"])
        result = analyze_build_deploy(inventory, tmp_path)

        gha_surfaces = [s for s in result if s.tool == "github-actions"]
        assert len(gha_surfaces) == 1
        assert gha_surfaces[0].config_type == "ci_cd"
        assert "lint" in gha_surfaces[0].stages
        assert "test" in gha_surfaces[0].stages


# ---------------------------------------------------------------------------
# GitLab CI detection
# ---------------------------------------------------------------------------


class TestGitLabCIDetection:
    """Detect GitLab CI config."""

    def test_gitlab_ci(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".gitlab-ci.yml",
            """\
            stages:
              - build
              - test
              - deploy
            build_job:
              stage: build
              script: make build
            """,
        )
        inventory = _make_inventory([".gitlab-ci.yml"])
        result = analyze_build_deploy(inventory, tmp_path)

        gitlab_surfaces = [s for s in result if s.tool == "gitlab-ci"]
        assert len(gitlab_surfaces) == 1
        assert gitlab_surfaces[0].config_type == "ci_cd"
        assert "build" in gitlab_surfaces[0].stages
        assert "test" in gitlab_surfaces[0].stages
        assert "deploy" in gitlab_surfaces[0].stages


# ---------------------------------------------------------------------------
# Jenkins detection
# ---------------------------------------------------------------------------


class TestJenkinsDetection:
    """Detect Jenkinsfile."""

    def test_jenkinsfile(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Jenkinsfile",
            """\
            pipeline {
                agent any
                stages {
                    stage('Build') { steps { sh 'make build' } }
                }
            }
            """,
        )
        inventory = _make_inventory(["Jenkinsfile"])
        result = analyze_build_deploy(inventory, tmp_path)

        jenkins_surfaces = [s for s in result if s.tool == "jenkins"]
        assert len(jenkins_surfaces) == 1
        assert jenkins_surfaces[0].config_type == "ci_cd"


# ---------------------------------------------------------------------------
# CircleCI detection
# ---------------------------------------------------------------------------


class TestCircleCIDetection:
    """Detect CircleCI config."""

    def test_circleci(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".circleci/config.yml",
            """\
            version: 2.1
            jobs:
              build:
                docker:
                  - image: python:3.12
            """,
        )
        inventory = _make_inventory([".circleci/config.yml"])
        result = analyze_build_deploy(inventory, tmp_path)

        circleci_surfaces = [s for s in result if s.tool == "circleci"]
        assert len(circleci_surfaces) == 1
        assert circleci_surfaces[0].config_type == "ci_cd"


# ---------------------------------------------------------------------------
# Makefile detection
# ---------------------------------------------------------------------------


class TestMakefileDetection:
    """Detect Makefile and extract targets."""

    def test_makefile_targets(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Makefile",
            """\
            build:
            \tgo build ./...

            test:
            \tgo test ./...

            lint:
            \tgolangci-lint run
            """,
        )
        inventory = _make_inventory(["Makefile"])
        result = analyze_build_deploy(inventory, tmp_path)

        make_surfaces = [s for s in result if s.tool == "make"]
        assert len(make_surfaces) == 1
        assert make_surfaces[0].config_type == "build_tool"
        assert "build" in make_surfaces[0].targets
        assert "test" in make_surfaces[0].targets
        assert "lint" in make_surfaces[0].targets


# ---------------------------------------------------------------------------
# justfile detection
# ---------------------------------------------------------------------------


class TestJustfileDetection:
    """Detect justfile and extract recipes."""

    def test_justfile_recipes(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "justfile",
            """\
            build:
                cargo build

            test:
                cargo test
            """,
        )
        inventory = _make_inventory(["justfile"])
        result = analyze_build_deploy(inventory, tmp_path)

        just_surfaces = [s for s in result if s.tool == "just"]
        assert len(just_surfaces) == 1
        assert "build" in just_surfaces[0].targets
        assert "test" in just_surfaces[0].targets


# ---------------------------------------------------------------------------
# package.json scripts detection
# ---------------------------------------------------------------------------


class TestPackageJsonDetection:
    """Detect package.json scripts section."""

    def test_package_json_scripts(self, tmp_path: Path) -> None:
        data = {
            "name": "my-app",
            "scripts": {
                "build": "tsc",
                "test": "jest",
                "start": "node dist/index.js",
            },
        }
        _write_file(tmp_path, "package.json", json.dumps(data))
        inventory = _make_inventory(["package.json"])
        result = analyze_build_deploy(inventory, tmp_path)

        npm_surfaces = [s for s in result if s.tool == "npm-scripts"]
        assert len(npm_surfaces) == 1
        assert "build" in npm_surfaces[0].targets
        assert "test" in npm_surfaces[0].targets
        assert "start" in npm_surfaces[0].targets

    def test_package_json_no_scripts(self, tmp_path: Path) -> None:
        data = {"name": "my-app", "version": "1.0.0"}
        _write_file(tmp_path, "package.json", json.dumps(data))
        inventory = _make_inventory(["package.json"])
        result = analyze_build_deploy(inventory, tmp_path)

        npm_surfaces = [s for s in result if s.tool == "npm-scripts"]
        assert len(npm_surfaces) == 0


# ---------------------------------------------------------------------------
# tox.ini detection
# ---------------------------------------------------------------------------


class TestToxDetection:
    """Detect tox.ini and extract environments."""

    def test_tox_envs(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "tox.ini",
            """\
            [tox]
            envlist = py312,lint

            [testenv]
            commands = pytest

            [testenv:lint]
            commands = ruff check
            """,
        )
        inventory = _make_inventory(["tox.ini"])
        result = analyze_build_deploy(inventory, tmp_path)

        tox_surfaces = [s for s in result if s.tool == "tox"]
        assert len(tox_surfaces) == 1
        assert "default" in tox_surfaces[0].targets
        assert "lint" in tox_surfaces[0].targets


# ---------------------------------------------------------------------------
# Kubernetes manifest detection
# ---------------------------------------------------------------------------


class TestKubernetesDetection:
    """Detect Kubernetes manifests and extract resource kinds."""

    def test_k8s_deployment(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "k8s/deployment.yaml",
            """\
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: my-app
            """,
        )
        inventory = _make_inventory(["k8s/deployment.yaml"])
        result = analyze_build_deploy(inventory, tmp_path)

        k8s_surfaces = [s for s in result if s.tool == "kubernetes"]
        assert len(k8s_surfaces) == 1
        assert k8s_surfaces[0].config_type == "iac"
        assert "Deployment" in k8s_surfaces[0].targets


# ---------------------------------------------------------------------------
# Terraform detection
# ---------------------------------------------------------------------------


class TestTerraformDetection:
    """Detect Terraform configs and extract resource types."""

    def test_terraform_resources(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "infra/main.tf",
            """\
            resource "aws_instance" "web" {
              ami           = "ami-12345"
              instance_type = "t3.micro"
            }

            resource "aws_s3_bucket" "data" {
              bucket = "my-bucket"
            }
            """,
        )
        inventory = _make_inventory(["infra/main.tf"])
        result = analyze_build_deploy(inventory, tmp_path)

        tf_surfaces = [s for s in result if s.tool == "terraform"]
        assert len(tf_surfaces) == 1
        assert tf_surfaces[0].config_type == "iac"
        assert "aws_instance" in tf_surfaces[0].targets
        assert "aws_s3_bucket" in tf_surfaces[0].targets


# ---------------------------------------------------------------------------
# Platform config detection
# ---------------------------------------------------------------------------


class TestPlatformConfigDetection:
    """Detect platform deployment configs."""

    def test_procfile(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "Procfile", "web: gunicorn app:app\n")
        inventory = _make_inventory(["Procfile"])
        result = analyze_build_deploy(inventory, tmp_path)

        heroku_surfaces = [s for s in result if s.tool == "heroku"]
        assert len(heroku_surfaces) == 1
        assert heroku_surfaces[0].config_type == "platform"

    def test_fly_toml(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "fly.toml", 'app = "my-app"\n')
        inventory = _make_inventory(["fly.toml"])
        result = analyze_build_deploy(inventory, tmp_path)

        fly_surfaces = [s for s in result if s.tool == "fly"]
        assert len(fly_surfaces) == 1
        assert fly_surfaces[0].config_type == "platform"

    def test_vercel_json(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "vercel.json", '{"builds": []}\n')
        inventory = _make_inventory(["vercel.json"])
        result = analyze_build_deploy(inventory, tmp_path)

        vercel_surfaces = [s for s in result if s.tool == "vercel"]
        assert len(vercel_surfaces) == 1
        assert vercel_surfaces[0].config_type == "platform"

    def test_netlify_toml(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "netlify.toml", '[build]\ncommand = "npm run build"\n')
        inventory = _make_inventory(["netlify.toml"])
        result = analyze_build_deploy(inventory, tmp_path)

        netlify_surfaces = [s for s in result if s.tool == "netlify"]
        assert len(netlify_surfaces) == 1
        assert netlify_surfaces[0].config_type == "platform"


# ---------------------------------------------------------------------------
# Surface type and serialization
# ---------------------------------------------------------------------------


class TestBuildDeploySurface:
    """Test BuildDeploySurface dataclass."""

    def test_surface_type_set(self) -> None:
        surface = BuildDeploySurface(name="Dockerfile")
        assert surface.surface_type == "build_deploy"

    def test_to_dict(self) -> None:
        surface = BuildDeploySurface(
            name="Dockerfile",
            config_type="container",
            tool="docker",
            stages=["builder"],
            targets=["python:3.12"],
        )
        d = surface.to_dict()
        assert d["config_type"] == "container"
        assert d["tool"] == "docker"
        assert d["stages"] == ["builder"]
        assert d["targets"] == ["python:3.12"]
        assert d["surface_type"] == "build_deploy"


# ---------------------------------------------------------------------------
# Multiple config types in one repo
# ---------------------------------------------------------------------------


class TestMultipleConfigTypes:
    """Test a repo with multiple build/deploy config types."""

    def test_mixed_configs(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "Dockerfile", "FROM python:3.12\nEXPOSE 8000\n")
        _write_file(
            tmp_path,
            ".github/workflows/ci.yml",
            "name: CI\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n",
        )
        _write_file(tmp_path, "Makefile", "build:\n\tpython -m build\n")
        _write_file(tmp_path, "fly.toml", 'app = "my-app"\n')

        inventory = _make_inventory(
            [
                "Dockerfile",
                ".github/workflows/ci.yml",
                "Makefile",
                "fly.toml",
            ]
        )
        result = analyze_build_deploy(inventory, tmp_path)

        tools = {s.tool for s in result}
        assert "docker" in tools
        assert "github-actions" in tools
        assert "make" in tools
        assert "fly" in tools
        assert len(result) >= 4
