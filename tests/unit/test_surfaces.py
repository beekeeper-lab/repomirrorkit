"""Unit tests for the surface data model."""

from __future__ import annotations

import json

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


class TestSourceRef:
    def test_creation_with_all_fields(self) -> None:
        ref = SourceRef(file_path="src/app.py", start_line=10, end_line=20)
        assert ref.file_path == "src/app.py"
        assert ref.start_line == 10
        assert ref.end_line == 20

    def test_creation_minimal(self) -> None:
        ref = SourceRef(file_path="src/app.py")
        assert ref.file_path == "src/app.py"
        assert ref.start_line is None
        assert ref.end_line is None

    def test_to_dict(self) -> None:
        ref = SourceRef(file_path="src/app.py", start_line=10, end_line=20)
        result = ref.to_dict()
        assert result == {
            "file_path": "src/app.py",
            "start_line": 10,
            "end_line": 20,
        }

    def test_frozen(self) -> None:
        ref = SourceRef(file_path="src/app.py")
        try:
            ref.file_path = "other.py"  # type: ignore[misc]
            raised = False
        except AttributeError:
            raised = True
        assert raised


class TestSurfaceBase:
    def test_creation(self) -> None:
        ref = SourceRef(file_path="src/app.py", start_line=1, end_line=5)
        surface = Surface(name="test", surface_type="base", source_refs=[ref])
        assert surface.name == "test"
        assert surface.surface_type == "base"
        assert len(surface.source_refs) == 1

    def test_default_source_refs(self) -> None:
        surface = Surface(name="test", surface_type="base")
        assert surface.source_refs == []

    def test_to_dict(self) -> None:
        ref = SourceRef(file_path="src/app.py", start_line=1, end_line=5)
        surface = Surface(name="test", surface_type="base", source_refs=[ref])
        result = surface.to_dict()
        assert result["name"] == "test"
        assert result["surface_type"] == "base"
        assert len(result["source_refs"]) == 1
        assert result["source_refs"][0]["file_path"] == "src/app.py"


class TestRouteSurface:
    def test_creation(self) -> None:
        route = RouteSurface(
            name="home",
            path="/home",
            method="GET",
            component_refs=["HomeView"],
            api_refs=["/api/data"],
            auth_requirements=["login_required"],
        )
        assert route.surface_type == "route"
        assert route.path == "/home"
        assert route.method == "GET"
        assert route.component_refs == ["HomeView"]
        assert route.api_refs == ["/api/data"]
        assert route.auth_requirements == ["login_required"]

    def test_to_dict(self) -> None:
        route = RouteSurface(
            name="home",
            path="/home",
            method="GET",
        )
        result = route.to_dict()
        assert result["surface_type"] == "route"
        assert result["path"] == "/home"
        assert result["method"] == "GET"
        assert result["component_refs"] == []
        assert result["api_refs"] == []
        assert result["auth_requirements"] == []

    def test_json_serializable(self) -> None:
        route = RouteSurface(name="home", path="/", method="GET")
        serialized = json.dumps(route.to_dict())
        assert isinstance(serialized, str)


class TestComponentSurface:
    def test_creation(self) -> None:
        comp = ComponentSurface(
            name="Sidebar",
            props=["items", "collapsed"],
            outputs=["item_selected"],
            usage_locations=["main_window.py"],
            states=["expanded", "collapsed"],
        )
        assert comp.surface_type == "component"
        assert comp.props == ["items", "collapsed"]
        assert comp.outputs == ["item_selected"]
        assert comp.usage_locations == ["main_window.py"]
        assert comp.states == ["expanded", "collapsed"]

    def test_to_dict(self) -> None:
        comp = ComponentSurface(name="Sidebar", props=["items"])
        result = comp.to_dict()
        assert result["surface_type"] == "component"
        assert result["props"] == ["items"]
        assert result["outputs"] == []


class TestApiSurface:
    def test_creation(self) -> None:
        api = ApiSurface(
            name="get_users",
            method="GET",
            path="/api/users",
            auth="bearer",
            request_schema={"page": "int"},
            response_schema={"users": "list"},
            side_effects=["audit_log"],
        )
        assert api.surface_type == "api"
        assert api.method == "GET"
        assert api.path == "/api/users"
        assert api.auth == "bearer"
        assert api.request_schema == {"page": "int"}
        assert api.response_schema == {"users": "list"}
        assert api.side_effects == ["audit_log"]

    def test_to_dict(self) -> None:
        api = ApiSurface(name="get_users", method="GET", path="/api/users")
        result = api.to_dict()
        assert result["surface_type"] == "api"
        assert result["method"] == "GET"
        assert result["request_schema"] == {}
        assert result["response_schema"] == {}


class TestModelSurface:
    def test_creation(self) -> None:
        model = ModelSurface(
            name="User",
            entity_name="User",
            fields=[
                ModelField(name="id", field_type="int", constraints=["primary_key"]),
                ModelField(name="email", field_type="str", constraints=["unique"]),
            ],
            relationships=["has_many:Order"],
            persistence_refs=["users_table"],
        )
        assert model.surface_type == "model"
        assert model.entity_name == "User"
        assert len(model.fields) == 2
        assert model.fields[0].name == "id"
        assert model.fields[0].constraints == ["primary_key"]

    def test_to_dict_includes_fields(self) -> None:
        model = ModelSurface(
            name="User",
            entity_name="User",
            fields=[ModelField(name="id", field_type="int")],
        )
        result = model.to_dict()
        assert result["surface_type"] == "model"
        assert result["entity_name"] == "User"
        assert result["fields"] == [
            {"name": "id", "field_type": "int", "constraints": []}
        ]

    def test_model_field_frozen(self) -> None:
        mf = ModelField(name="id", field_type="int")
        try:
            mf.name = "other"  # type: ignore[misc]
            raised = False
        except AttributeError:
            raised = True
        assert raised


class TestAuthSurface:
    def test_creation(self) -> None:
        auth = AuthSurface(
            name="admin_auth",
            roles=["admin", "superadmin"],
            permissions=["read", "write", "delete"],
            rules=["require_mfa"],
            protected_endpoints=["/api/admin"],
        )
        assert auth.surface_type == "auth"
        assert auth.roles == ["admin", "superadmin"]
        assert auth.permissions == ["read", "write", "delete"]
        assert auth.rules == ["require_mfa"]
        assert auth.protected_endpoints == ["/api/admin"]

    def test_to_dict(self) -> None:
        auth = AuthSurface(name="basic_auth", roles=["user"])
        result = auth.to_dict()
        assert result["surface_type"] == "auth"
        assert result["roles"] == ["user"]
        assert result["permissions"] == []


class TestConfigSurface:
    def test_creation(self) -> None:
        config = ConfigSurface(
            name="DATABASE_URL",
            env_var_name="DATABASE_URL",
            default_value="sqlite:///db.sqlite3",
            required=True,
            usage_locations=["config.py", "db.py"],
        )
        assert config.surface_type == "config"
        assert config.env_var_name == "DATABASE_URL"
        assert config.default_value == "sqlite:///db.sqlite3"
        assert config.required is True
        assert config.usage_locations == ["config.py", "db.py"]

    def test_to_dict(self) -> None:
        config = ConfigSurface(
            name="DEBUG",
            env_var_name="DEBUG",
            default_value="false",
            required=False,
        )
        result = config.to_dict()
        assert result["surface_type"] == "config"
        assert result["env_var_name"] == "DEBUG"
        assert result["default_value"] == "false"
        assert result["required"] is False

    def test_default_value_none(self) -> None:
        config = ConfigSurface(name="SECRET", env_var_name="SECRET", required=True)
        assert config.default_value is None
        result = config.to_dict()
        assert result["default_value"] is None


class TestCrosscuttingSurface:
    def test_creation(self) -> None:
        cc = CrosscuttingSurface(
            name="logging",
            concern_type="logging",
            description="Structured logging across all services",
            affected_files=["app.py", "api.py", "worker.py"],
        )
        assert cc.surface_type == "crosscutting"
        assert cc.concern_type == "logging"
        assert cc.description == "Structured logging across all services"
        assert len(cc.affected_files) == 3

    def test_to_dict(self) -> None:
        cc = CrosscuttingSurface(
            name="error_handling",
            concern_type="error-handling",
            description="Global error handler",
        )
        result = cc.to_dict()
        assert result["surface_type"] == "crosscutting"
        assert result["concern_type"] == "error-handling"
        assert result["affected_files"] == []


class TestSurfaceCollection:
    def _make_collection(self) -> SurfaceCollection:
        return SurfaceCollection(
            routes=[RouteSurface(name="home", path="/", method="GET")],
            components=[ComponentSurface(name="Sidebar")],
            apis=[ApiSurface(name="get_users", method="GET", path="/api/users")],
            models=[ModelSurface(name="User", entity_name="User")],
            auth=[AuthSurface(name="basic", roles=["user"])],
            config=[ConfigSurface(name="DEBUG", env_var_name="DEBUG")],
            crosscutting=[CrosscuttingSurface(name="logging", concern_type="logging")],
        )

    def test_iteration(self) -> None:
        coll = self._make_collection()
        surfaces = list(coll)
        assert len(surfaces) == 7
        types = {s.surface_type for s in surfaces}
        assert types == {
            "route",
            "component",
            "api",
            "model",
            "auth",
            "config",
            "crosscutting",
        }

    def test_len(self) -> None:
        coll = self._make_collection()
        assert len(coll) == 7

    def test_empty_collection(self) -> None:
        coll = SurfaceCollection()
        assert len(coll) == 0
        assert list(coll) == []

    def test_to_dict(self) -> None:
        coll = self._make_collection()
        result = coll.to_dict()
        assert len(result["routes"]) == 1
        assert len(result["components"]) == 1
        assert len(result["apis"]) == 1
        assert len(result["models"]) == 1
        assert len(result["auth"]) == 1
        assert len(result["config"]) == 1
        assert len(result["crosscutting"]) == 1

    def test_to_json(self) -> None:
        coll = self._make_collection()
        json_str = coll.to_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert "routes" in parsed
        assert len(parsed["routes"]) == 1

    def test_to_dict_empty(self) -> None:
        coll = SurfaceCollection()
        result = coll.to_dict()
        for key in [
            "routes",
            "components",
            "apis",
            "models",
            "auth",
            "config",
            "crosscutting",
        ]:
            assert result[key] == []

    def test_json_round_trip(self) -> None:
        coll = self._make_collection()
        json_str = coll.to_json()
        parsed = json.loads(json_str)
        json_again = json.dumps(parsed, indent=2)
        assert json.loads(json_again) == json.loads(json_str)

    def test_multiple_surfaces_per_type(self) -> None:
        coll = SurfaceCollection(
            routes=[
                RouteSurface(name="home", path="/", method="GET"),
                RouteSurface(name="about", path="/about", method="GET"),
            ],
        )
        assert len(coll) == 2
        assert len(list(coll)) == 2

    def test_surface_with_source_refs(self) -> None:
        ref = SourceRef(file_path="routes.py", start_line=10, end_line=15)
        route = RouteSurface(name="home", path="/", method="GET", source_refs=[ref])
        coll = SurfaceCollection(routes=[route])
        result = coll.to_dict()
        assert result["routes"][0]["source_refs"][0]["file_path"] == "routes.py"
        assert result["routes"][0]["source_refs"][0]["start_line"] == 10
