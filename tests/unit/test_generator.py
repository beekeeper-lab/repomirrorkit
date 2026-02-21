"""Unit tests for the generator package (CLAUDE.md, agents, stacks, assembler)."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    BuildDeploySurface,
    ComponentSurface,
    DependencySurface,
    ModelSurface,
    RouteSurface,
    SourceRef,
    SurfaceCollection,
    TestPatternSurface,
)
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.generator.agents import generate_agents
from repo_mirror_kit.harvester.generator.assembler import assemble_project_folder
from repo_mirror_kit.harvester.generator.claude_md import generate_claude_md
from repo_mirror_kit.harvester.generator.stacks import generate_stacks

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ref(path: str = "src/app.py") -> SourceRef:
    return SourceRef(file_path=path, start_line=1, end_line=10)


def _make_profile(stacks: dict[str, float] | None = None) -> StackProfile:
    return StackProfile(
        stacks={"python": 0.9, "fastapi": 0.8} if stacks is None else stacks,
        evidence={},
        signals=[],
    )


def _make_surfaces(
    *,
    routes: int = 2,
    apis: int = 3,
    components: int = 1,
    models: int = 2,
    auth: int = 0,
    build_deploy: int = 0,
    dependencies: int = 1,
    test_patterns: int = 1,
) -> SurfaceCollection:
    return SurfaceCollection(
        routes=[
            RouteSurface(
                name=f"Route{i}",
                path=f"/r{i}",
                method="GET",
                source_refs=[_make_ref()],
            )
            for i in range(routes)
        ],
        apis=[
            ApiSurface(
                name=f"API{i}",
                path=f"/api/{i}",
                method="POST",
                source_refs=[_make_ref()],
            )
            for i in range(apis)
        ],
        components=[
            ComponentSurface(
                name=f"Comp{i}",
                source_refs=[_make_ref()],
            )
            for i in range(components)
        ],
        models=[
            ModelSurface(
                name=f"Model{i}",
                entity_name=f"Model{i}",
                source_refs=[_make_ref()],
            )
            for i in range(models)
        ],
        auth=[
            AuthSurface(
                name=f"Auth{i}",
                source_refs=[_make_ref()],
            )
            for i in range(auth)
        ],
        build_deploy=[
            BuildDeploySurface(
                name=f"Build{i}",
                tool="docker",
                source_refs=[_make_ref("Dockerfile")],
            )
            for i in range(build_deploy)
        ],
        dependencies=[
            DependencySurface(
                name=f"dep{i}",
                manifest_file="pyproject.toml",
                source_refs=[_make_ref("pyproject.toml")],
            )
            for i in range(dependencies)
        ],
        test_patterns=[
            TestPatternSurface(
                name=f"Test{i}",
                framework="pytest",
                test_type="unit",
                test_file=f"tests/test_{i}.py",
                test_count=5,
                source_refs=[_make_ref(f"tests/test_{i}.py")],
            )
            for i in range(test_patterns)
        ],
    )


# ---------------------------------------------------------------------------
# CLAUDE.md generation
# ---------------------------------------------------------------------------


class TestClaudeMdGeneration:
    """Tests for claude_md.py generator."""

    def test_includes_project_name(self) -> None:
        surfaces = _make_surfaces()
        profile = _make_profile()
        result = generate_claude_md("MyProject", surfaces, profile, [], [])
        assert "# MyProject" in result

    def test_includes_tech_stack(self) -> None:
        surfaces = _make_surfaces()
        profile = _make_profile({"python": 0.9, "fastapi": 0.8})
        result = generate_claude_md("MyProject", surfaces, profile, [], [])
        assert "fastapi" in result
        assert "python" in result

    def test_includes_safety_rules(self) -> None:
        surfaces = _make_surfaces()
        profile = _make_profile()
        result = generate_claude_md("MyProject", surfaces, profile, [], [])
        assert "Safety Rules" in result
        assert "No secrets in code" in result

    def test_includes_quality_rules(self) -> None:
        surfaces = _make_surfaces()
        profile = _make_profile()
        result = generate_claude_md("MyProject", surfaces, profile, [], [])
        assert "Quality Rules" in result
        assert "Testability" in result

    def test_includes_team_roster(self) -> None:
        agents = [
            {"name": "Developer", "file": ".claude/agents/developer.md"},
            {"name": "Architect", "file": ".claude/agents/architect.md"},
        ]
        surfaces = _make_surfaces()
        profile = _make_profile()
        result = generate_claude_md("MyProject", surfaces, profile, agents, [])
        assert "Team Roster" in result
        assert "Developer" in result
        assert ".claude/agents/developer.md" in result

    def test_includes_workflow_reference(self) -> None:
        surfaces = _make_surfaces()
        profile = _make_profile()
        result = generate_claude_md(
            "MyProject", surfaces, profile, [], ["ai/stacks/python.md"]
        )
        assert "Workflow Reference" in result
        assert "surface-map.md" in result
        assert "ai/stacks/python.md" in result

    def test_auth_surfaces_add_auth_safety_rule(self) -> None:
        surfaces = _make_surfaces(auth=2)
        profile = _make_profile()
        result = generate_claude_md("MyProject", surfaces, profile, [], [])
        assert "Auth on every endpoint" in result

    def test_model_surfaces_add_query_safety_rule(self) -> None:
        surfaces = _make_surfaces(models=3)
        profile = _make_profile()
        result = generate_claude_md("MyProject", surfaces, profile, [], [])
        assert "Parameterize queries" in result

    def test_empty_stacks_handled(self) -> None:
        surfaces = _make_surfaces()
        profile = _make_profile({})
        result = generate_claude_md("MyProject", surfaces, profile, [], [])
        assert "# MyProject" in result
        assert "unknown" in result

    def test_stack_reference_includes_test_framework(self) -> None:
        surfaces = _make_surfaces(test_patterns=2)
        profile = _make_profile()
        result = generate_claude_md("MyProject", surfaces, profile, [], [])
        assert "pytest" in result

    def test_stack_reference_includes_build_tools(self) -> None:
        surfaces = _make_surfaces(build_deploy=1)
        profile = _make_profile()
        result = generate_claude_md("MyProject", surfaces, profile, [], [])
        assert "docker" in result


# ---------------------------------------------------------------------------
# Stack generation
# ---------------------------------------------------------------------------


class TestStackGeneration:
    """Tests for stacks.py generator."""

    def test_python_stack_generated(self) -> None:
        profile = _make_profile({"python": 0.9})
        surfaces = _make_surfaces()
        stacks = generate_stacks(profile, surfaces)
        assert len(stacks) >= 1
        python_stacks = [s for s in stacks if "python" in s.relative_path]
        assert len(python_stacks) == 1
        assert "Python" in python_stacks[0].content

    def test_js_stack_generated(self) -> None:
        profile = _make_profile({"react": 0.9, "typescript": 0.8})
        surfaces = _make_surfaces()
        stacks = generate_stacks(profile, surfaces)
        ts_stacks = [s for s in stacks if "typescript" in s.relative_path]
        assert len(ts_stacks) == 1
        assert "TypeScript" in ts_stacks[0].content

    def test_dotnet_stack_generated(self) -> None:
        profile = _make_profile({"dotnet": 0.9})
        surfaces = _make_surfaces()
        stacks = generate_stacks(profile, surfaces)
        dotnet_stacks = [s for s in stacks if "dotnet" in s.relative_path]
        assert len(dotnet_stacks) == 1
        assert "C#" in dotnet_stacks[0].content

    def test_go_stack_generated(self) -> None:
        profile = _make_profile({"go": 0.9})
        surfaces = _make_surfaces()
        stacks = generate_stacks(profile, surfaces)
        go_stacks = [s for s in stacks if "go" in s.relative_path]
        assert len(go_stacks) == 1
        assert "Go" in go_stacks[0].content

    def test_ruby_stack_generated(self) -> None:
        profile = _make_profile({"ruby": 0.9})
        surfaces = _make_surfaces()
        stacks = generate_stacks(profile, surfaces)
        ruby_stacks = [s for s in stacks if "ruby" in s.relative_path]
        assert len(ruby_stacks) == 1
        assert "Ruby" in ruby_stacks[0].content

    def test_generic_stack_fallback(self) -> None:
        profile = _make_profile({"exotic_lang": 0.9})
        surfaces = _make_surfaces()
        stacks = generate_stacks(profile, surfaces)
        assert len(stacks) == 1
        assert "conventions" in stacks[0].relative_path

    def test_multiple_stacks_detected(self) -> None:
        profile = _make_profile({"python": 0.9, "react": 0.8, "typescript": 0.7})
        surfaces = _make_surfaces()
        stacks = generate_stacks(profile, surfaces)
        assert len(stacks) >= 2

    def test_stack_file_has_relative_path(self) -> None:
        profile = _make_profile({"python": 0.9})
        surfaces = _make_surfaces()
        stacks = generate_stacks(profile, surfaces)
        assert all(s.relative_path.startswith("ai/stacks/") for s in stacks)

    def test_python_stack_detects_fastapi(self) -> None:
        profile = _make_profile({"python": 0.9, "fastapi": 0.8})
        surfaces = _make_surfaces()
        stacks = generate_stacks(profile, surfaces)
        python_stacks = [s for s in stacks if "python" in s.relative_path]
        assert "FastAPI" in python_stacks[0].content

    def test_nextjs_detected(self) -> None:
        profile = _make_profile({"nextjs": 0.9, "react": 0.8})
        surfaces = _make_surfaces()
        stacks = generate_stacks(profile, surfaces)
        js_stacks = [s for s in stacks if "javascript" in s.relative_path]
        assert len(js_stacks) == 1
        assert "Next.js" in js_stacks[0].content


# ---------------------------------------------------------------------------
# Agent generation
# ---------------------------------------------------------------------------


class TestAgentGeneration:
    """Tests for agents.py generator."""

    def test_always_generates_three_base_agents(self) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces()
        agents = generate_agents("MyProject", profile, surfaces, [])
        assert len(agents) >= 3
        names = {a.name for a in agents}
        assert "Developer" in names
        assert "Software Architect" in names
        assert "Tech-QA / Test Engineer" in names

    def test_security_agent_when_auth_exists(self) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces(auth=2)
        agents = generate_agents("MyProject", profile, surfaces, [])
        names = {a.name for a in agents}
        assert "Security Engineer" in names

    def test_no_security_agent_without_auth(self) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces(auth=0)
        agents = generate_agents("MyProject", profile, surfaces, [])
        names = {a.name for a in agents}
        assert "Security Engineer" not in names

    def test_devops_agent_when_build_deploy_exists(self) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces(build_deploy=2)
        agents = generate_agents("MyProject", profile, surfaces, [])
        names = {a.name for a in agents}
        assert "DevOps / Release Engineer" in names

    def test_no_devops_agent_without_build_deploy(self) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces(build_deploy=0)
        agents = generate_agents("MyProject", profile, surfaces, [])
        names = {a.name for a in agents}
        assert "DevOps / Release Engineer" not in names

    def test_developer_agent_includes_stack(self) -> None:
        profile = _make_profile({"python": 0.9, "fastapi": 0.8})
        surfaces = _make_surfaces()
        agents = generate_agents("MyProject", profile, surfaces, [])
        dev = next(a for a in agents if a.name == "Developer")
        assert "fastapi" in dev.content
        assert "python" in dev.content

    def test_architect_agent_includes_surface_counts(self) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces(routes=5, apis=10, models=3, components=7)
        agents = generate_agents("MyProject", profile, surfaces, [])
        arch = next(a for a in agents if a.name == "Software Architect")
        assert "Components:** 7" in arch.content
        assert "API endpoints:** 10" in arch.content

    def test_tech_qa_agent_includes_test_info(self) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces(test_patterns=3)
        agents = generate_agents("MyProject", profile, surfaces, [])
        qa = next(a for a in agents if a.name == "Tech-QA / Test Engineer")
        assert "pytest" in qa.content

    def test_agent_paths_are_valid(self) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces()
        agents = generate_agents("MyProject", profile, surfaces, [])
        for agent in agents:
            assert agent.relative_path.startswith(".claude/agents/")
            assert agent.relative_path.endswith(".md")

    def test_all_agents_when_full_surfaces(self) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces(auth=1, build_deploy=1)
        agents = generate_agents("MyProject", profile, surfaces, [])
        assert len(agents) == 5  # dev + arch + qa + sec + devops


# ---------------------------------------------------------------------------
# Assembler
# ---------------------------------------------------------------------------


class TestAssembler:
    """Tests for assembler.py orchestrator."""

    def test_creates_project_folder(self, tmp_path: Path) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces()
        result = assemble_project_folder(
            tmp_path,
            "TestProject",
            surfaces,
            profile,
        )
        assert result.output_dir.exists()
        assert (result.output_dir / "CLAUDE.md").exists()

    def test_creates_agent_files(self, tmp_path: Path) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces()
        result = assemble_project_folder(
            tmp_path,
            "TestProject",
            surfaces,
            profile,
        )
        agent_dir = result.output_dir / ".claude" / "agents"
        assert agent_dir.exists()
        assert (agent_dir / "developer.md").exists()
        assert (agent_dir / "architect.md").exists()
        assert (agent_dir / "tech-qa.md").exists()

    def test_creates_stack_files(self, tmp_path: Path) -> None:
        profile = _make_profile({"python": 0.9})
        surfaces = _make_surfaces()
        result = assemble_project_folder(
            tmp_path,
            "TestProject",
            surfaces,
            profile,
        )
        assert result.stack_count >= 1
        stack_dir = result.output_dir / "ai" / "stacks"
        assert stack_dir.exists()

    def test_result_counts(self, tmp_path: Path) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces()
        result = assemble_project_folder(
            tmp_path,
            "TestProject",
            surfaces,
            profile,
        )
        assert result.agent_count >= 3
        assert result.stack_count >= 1
        # total = agents + stacks + CLAUDE.md
        assert (
            len(result.generated_files) == result.agent_count + result.stack_count + 1
        )

    def test_conditional_agents(self, tmp_path: Path) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces(auth=1, build_deploy=1)
        result = assemble_project_folder(
            tmp_path,
            "TestProject",
            surfaces,
            profile,
        )
        assert result.agent_count == 5
        agent_dir = result.output_dir / ".claude" / "agents"
        assert (agent_dir / "security-engineer.md").exists()
        assert (agent_dir / "devops-release.md").exists()

    def test_claude_md_contains_project_name(self, tmp_path: Path) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces()
        result = assemble_project_folder(
            tmp_path,
            "TestProject",
            surfaces,
            profile,
        )
        content = (result.output_dir / "CLAUDE.md").read_text()
        assert "# TestProject" in content

    def test_claude_md_references_agents(self, tmp_path: Path) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces()
        result = assemble_project_folder(
            tmp_path,
            "TestProject",
            surfaces,
            profile,
        )
        content = (result.output_dir / "CLAUDE.md").read_text()
        assert "Developer" in content
        assert ".claude/agents/developer.md" in content

    def test_generated_files_are_valid_markdown(self, tmp_path: Path) -> None:
        profile = _make_profile()
        surfaces = _make_surfaces()
        result = assemble_project_folder(
            tmp_path,
            "TestProject",
            surfaces,
            profile,
        )
        for path in result.generated_files:
            content = path.read_text()
            assert content.strip(), f"File {path} is empty"
            # Basic markdown validity: no broken reference patterns
            assert "{{" not in content, f"File {path} has template artifacts"

    def test_empty_surfaces_still_generates(self, tmp_path: Path) -> None:
        profile = _make_profile()
        surfaces = SurfaceCollection()
        result = assemble_project_folder(
            tmp_path,
            "TestProject",
            surfaces,
            profile,
        )
        assert result.output_dir.exists()
        assert (result.output_dir / "CLAUDE.md").exists()
        assert result.agent_count >= 3


# ---------------------------------------------------------------------------
# Pipeline integration (_derive_project_name)
# ---------------------------------------------------------------------------


class TestDeriveProjectName:
    """Tests for project name derivation from repo URLs."""

    def test_github_https_url(self) -> None:
        from repo_mirror_kit.harvester.pipeline import _derive_project_name

        assert _derive_project_name("https://github.com/user/myrepo.git") == "myrepo"

    def test_github_https_no_git_suffix(self) -> None:
        from repo_mirror_kit.harvester.pipeline import _derive_project_name

        assert _derive_project_name("https://github.com/user/myrepo") == "myrepo"

    def test_trailing_slash(self) -> None:
        from repo_mirror_kit.harvester.pipeline import _derive_project_name

        assert _derive_project_name("https://github.com/user/myrepo/") == "myrepo"

    def test_local_path(self) -> None:
        from repo_mirror_kit.harvester.pipeline import _derive_project_name

        assert _derive_project_name("/home/user/projects/myrepo") == "myrepo"

    def test_empty_string(self) -> None:
        from repo_mirror_kit.harvester.pipeline import _derive_project_name

        assert _derive_project_name("") == "project"
