"""Unit tests for the auth & security analyzer."""

from __future__ import annotations

import textwrap
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.auth import analyze_auth
from repo_mirror_kit.harvester.analyzers.surfaces import AuthSurface
from repo_mirror_kit.harvester.detectors.base import StackProfile
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


def _make_profile(stacks: dict[str, float]) -> StackProfile:
    """Build a StackProfile with the given stacks."""
    return StackProfile(
        stacks=stacks,
        evidence={name: [] for name in stacks},
        signals=[],
    )


def _write_file(workdir: Path, rel_path: str, content: str) -> None:
    """Write a file under workdir with the given content."""
    full = workdir / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(textwrap.dedent(content), encoding="utf-8")


# ---------------------------------------------------------------------------
# No-op when no frameworks detected
# ---------------------------------------------------------------------------


class TestNoFrameworkDetected:
    """Analyzer returns empty when no relevant frameworks detected."""

    def test_empty_profile(self, tmp_path: Path) -> None:
        inventory = _make_inventory([])
        profile = _make_profile({})
        result = analyze_auth(inventory, profile, tmp_path)
        assert result == []

    def test_unrelated_stack(self, tmp_path: Path) -> None:
        inventory = _make_inventory(["src/app.py"])
        profile = _make_profile({"react": 0.9})
        result = analyze_auth(inventory, profile, tmp_path)
        assert result == []


# ---------------------------------------------------------------------------
# Express / Node auth patterns
# ---------------------------------------------------------------------------


class TestExpressAuth:
    """Extract Express/Node auth patterns."""

    def test_passport_strategy(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "auth/passport.js",
            """\
            const passport = require('passport');
            const LocalStrategy = require('passport-local');
            passport.use(new LocalStrategy(function(username, password, done) {
                User.findOne({ username }, function(err, user) { done(err, user); });
            }));
            """,
        )
        inventory = _make_inventory(["auth/passport.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert surfaces[0].name == "express_auth"
        assert any("passport:LocalStrategy" in r for r in surfaces[0].rules)

    def test_passport_authenticate(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "middleware/auth.js",
            """\
            const passport = require('passport');
            module.exports = passport.authenticate('jwt', { session: false });
            """,
        )
        inventory = _make_inventory(["middleware/auth.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert any("passport.authenticate:jwt" in r for r in surfaces[0].rules)

    def test_is_authenticated(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "middleware/check.js",
            """\
            function ensureAuth(req, res, next) {
                if (req.isAuthenticated()) { return next(); }
                res.redirect('/login');
            }
            """,
        )
        inventory = _make_inventory(["middleware/check.js"])
        profile = _make_profile({"express": 0.7})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "isAuthenticated" in surfaces[0].rules

    def test_role_extraction(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "middleware/roles.js",
            """\
            function requireRole(req, res, next) {
                if (hasRole('admin')) next();
            }
            function checkManager(req, res, next) {
                if (hasRole('manager')) next();
            }
            """,
        )
        inventory = _make_inventory(["middleware/roles.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "admin" in surfaces[0].roles
        assert "manager" in surfaces[0].roles

    def test_jwt_token_type(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "auth/jwt.js",
            """\
            const jwt = require('jsonwebtoken');
            passport.use(new JwtStrategy(opts, verify));
            """,
        )
        inventory = _make_inventory(["auth/jwt.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert any("token_type:jwt" in r for r in surfaces[0].rules)

    def test_session_token_type(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "middleware/session.js",
            """\
            const session = require('express-session');
            app.use(session({ secret: 'mysecret' }));
            if (req.isAuthenticated()) { next(); }
            """,
        )
        inventory = _make_inventory(["middleware/session.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert any("token_type:session" in r for r in surfaces[0].rules)

    def test_fastify_triggers_express_extractor(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "auth/verify.js",
            """\
            if (req.isAuthenticated()) { return next(); }
            """,
        )
        inventory = _make_inventory(["auth/verify.js"])
        profile = _make_profile({"fastify": 0.7})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert surfaces[0].name == "express_auth"

    def test_no_auth_files_returns_empty(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "src/index.js", "console.log('hello');")
        inventory = _make_inventory(["src/index.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert surfaces == []


# ---------------------------------------------------------------------------
# FastAPI auth patterns
# ---------------------------------------------------------------------------


class TestFastapiAuth:
    """Extract FastAPI auth patterns."""

    def test_depends_auth(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "dependencies/auth.py",
            """\
            from fastapi import Depends
            async def get_current_user(token: str = Depends(verify_token)):
                return token
            """,
        )
        inventory = _make_inventory(["dependencies/auth.py"])
        profile = _make_profile({"fastapi": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert surfaces[0].name == "fastapi_auth"
        assert any("Depends:verify_token" in r for r in surfaces[0].rules)

    def test_oauth2_security_scheme(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "security/oauth.py",
            """\
            from fastapi.security import OAuth2PasswordBearer
            oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
            """,
        )
        inventory = _make_inventory(["security/oauth.py"])
        profile = _make_profile({"fastapi": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert any("security:" in r for r in surfaces[0].rules)

    def test_role_scopes(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "auth/roles.py",
            """\
            from fastapi import Depends, Security

            async def get_current_user(token = Depends(auth_handler)):
                pass

            scopes = ['read', 'write', 'admin']
            """,
        )
        inventory = _make_inventory(["auth/roles.py"])
        profile = _make_profile({"fastapi": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "read" in surfaces[0].roles
        assert "write" in surfaces[0].roles
        assert "admin" in surfaces[0].roles

    def test_no_auth_in_deps(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "dependencies/database.py",
            """\
            from fastapi import Depends
            def get_db():
                return Database()
            """,
        )
        inventory = _make_inventory(["dependencies/database.py"])
        profile = _make_profile({"fastapi": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert surfaces == []


# ---------------------------------------------------------------------------
# Flask auth patterns
# ---------------------------------------------------------------------------


class TestFlaskAuth:
    """Extract Flask auth patterns."""

    def test_login_required(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "views/dashboard.py",
            """\
            from flask_login import login_required

            @app.route('/dashboard')
            @login_required
            def dashboard():
                return render_template('dashboard.html')
            """,
        )
        inventory = _make_inventory(["views/dashboard.py"])
        profile = _make_profile({"flask": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert surfaces[0].name == "flask_auth"
        assert "login_required" in surfaces[0].rules

    def test_roles_required(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "views/admin.py",
            """\
            from flask_principal import roles_required

            @app.route('/admin')
            @roles_required('admin', 'superadmin')
            def admin_panel():
                return render_template('admin.html')
            """,
        )
        inventory = _make_inventory(["views/admin.py"])
        profile = _make_profile({"flask": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "admin" in surfaces[0].roles
        assert "superadmin" in surfaces[0].roles
        assert "roles_required" in surfaces[0].rules

    def test_login_manager(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "app.py",
            """\
            from flask_login import LoginManager
            login_manager = LoginManager()
            login_manager.init_app(app)
            """,
        )
        inventory = _make_inventory(["app.py"])
        profile = _make_profile({"flask": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "flask_login:LoginManager" in surfaces[0].rules

    def test_current_user(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "views/profile.py",
            """\
            from flask_login import current_user

            @app.route('/profile')
            def profile():
                if current_user.is_authenticated:
                    return render_template('profile.html')
            """,
        )
        inventory = _make_inventory(["views/profile.py"])
        profile = _make_profile({"flask": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "current_user" in surfaces[0].rules

    def test_no_auth_in_views(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "views/home.py",
            """\
            @app.route('/')
            def home():
                return render_template('home.html')
            """,
        )
        inventory = _make_inventory(["views/home.py"])
        profile = _make_profile({"flask": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert surfaces == []


# ---------------------------------------------------------------------------
# Next.js / NextAuth patterns
# ---------------------------------------------------------------------------


class TestNextjsAuth:
    """Extract Next.js/NextAuth auth patterns."""

    def test_nextauth_config(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "pages/api/auth/[...nextauth].ts",
            """\
            import NextAuth from 'next-auth';
            import GithubProvider from 'next-auth/providers/github';

            export default NextAuth({
                providers: [GithubProvider({ clientId: '...' })],
            });
            """,
        )
        inventory = _make_inventory(["pages/api/auth/[...nextauth].ts"])
        profile = _make_profile({"nextjs": 0.9})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert surfaces[0].name == "nextjs_auth"
        assert "nextauth" in surfaces[0].rules
        assert any("provider:GithubProvider" in r for r in surfaces[0].rules)

    def test_middleware_auth(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "middleware.ts",
            """\
            import { NextResponse } from 'next/server';
            export const config = {
                matcher: ['/protected/:path*', '/api/auth/:path*'],
            };
            """,
        )
        inventory = _make_inventory(["middleware.ts"])
        profile = _make_profile({"nextjs": 0.9})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "middleware_auth" in surfaces[0].rules

    def test_get_server_session(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "lib/auth.ts",
            """\
            import { getServerSession } from 'next-auth';
            export async function requireAuth() {
                const session = await getServerSession();
                if (!session) throw new Error('Unauthorized');
            }
            """,
        )
        inventory = _make_inventory(["lib/auth.ts"])
        profile = _make_profile({"nextjs": 0.9})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "nextauth" in surfaces[0].rules

    def test_use_session(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "lib/auth.ts",
            """\
            import { useSession } from 'next-auth/react';
            export function AuthButton() {
                const { data: session } = useSession();
                return session ? <Logout /> : <Login />;
            }
            """,
        )
        inventory = _make_inventory(["lib/auth.ts"])
        profile = _make_profile({"nextjs": 0.9})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "nextauth" in surfaces[0].rules

    def test_no_auth_in_middleware(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "middleware.ts",
            """\
            import { NextResponse } from 'next/server';
            export function middleware(request) {
                return NextResponse.next();
            }
            """,
        )
        inventory = _make_inventory(["middleware.ts"])
        profile = _make_profile({"nextjs": 0.9})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert surfaces == []


# ---------------------------------------------------------------------------
# NestJS auth patterns
# ---------------------------------------------------------------------------


class TestNestjsAuth:
    """Extract NestJS auth patterns."""

    def test_use_guards(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/auth/auth.guard.ts",
            """\
            import { UseGuards } from '@nestjs/common';
            @UseGuards(AuthGuard)
            @Controller('users')
            export class UsersController {}
            """,
        )
        inventory = _make_inventory(["src/auth/auth.guard.ts"])
        profile = _make_profile({"nestjs": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert surfaces[0].name == "nestjs_auth"
        assert any("UseGuards:AuthGuard" in r for r in surfaces[0].rules)
        assert "AuthGuard" in surfaces[0].rules

    def test_roles_decorator(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/auth/roles.guard.ts",
            """\
            import { Roles } from './roles.decorator';
            @Roles('admin', 'editor')
            @UseGuards(RolesGuard)
            async deleteUser() {}
            """,
        )
        inventory = _make_inventory(["src/auth/roles.guard.ts"])
        profile = _make_profile({"nestjs": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "admin" in surfaces[0].roles
        assert "editor" in surfaces[0].roles

    def test_passport_strategy(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/auth/jwt.strategy.ts",
            """\
            import { PassportStrategy } from '@nestjs/passport';
            export class JwtStrategy extends PassportStrategy(Strategy) {
                constructor() { super({ jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken() }); }
            }
            """,
        )
        inventory = _make_inventory(["src/auth/jwt.strategy.ts"])
        profile = _make_profile({"nestjs": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "PassportStrategy" in surfaces[0].rules

    def test_no_auth_in_service(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/users/users.service.ts",
            """\
            @Injectable()
            export class UsersService {
                findAll() { return this.usersRepository.find(); }
            }
            """,
        )
        # Note: users.service.ts doesn't match auth file patterns
        inventory = _make_inventory(["src/users/users.service.ts"])
        profile = _make_profile({"nestjs": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert surfaces == []


# ---------------------------------------------------------------------------
# .NET auth patterns
# ---------------------------------------------------------------------------


class TestDotnetAuth:
    """Extract .NET authorization patterns."""

    def test_authorize_attribute(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Controllers/UsersController.cs",
            """\
            using Microsoft.AspNetCore.Authorization;

            [Authorize]
            [ApiController]
            [Route("api/[controller]")]
            public class UsersController : ControllerBase
            {
                [HttpGet]
                public IActionResult GetAll() => Ok();
            }
            """,
        )
        inventory = _make_inventory(["Controllers/UsersController.cs"])
        profile = _make_profile({"aspnet": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert surfaces[0].name == "dotnet_auth"
        assert "Authorize" in surfaces[0].rules

    def test_authorize_with_roles(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Controllers/AdminController.cs",
            """\
            [Authorize(Roles = "Admin,SuperAdmin")]
            [ApiController]
            public class AdminController : ControllerBase
            {
                [HttpDelete("{id}")]
                public IActionResult Delete(int id) => Ok();
            }
            """,
        )
        inventory = _make_inventory(["Controllers/AdminController.cs"])
        profile = _make_profile({"aspnet": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "Admin" in surfaces[0].roles
        assert "SuperAdmin" in surfaces[0].roles

    def test_authorize_with_policy(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Controllers/ReportsController.cs",
            """\
            [Authorize(Policy = "CanViewReports")]
            [ApiController]
            public class ReportsController : ControllerBase {}
            """,
        )
        inventory = _make_inventory(["Controllers/ReportsController.cs"])
        profile = _make_profile({"aspnet": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "CanViewReports" in surfaces[0].permissions

    def test_allow_anonymous(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Controllers/PublicController.cs",
            """\
            [Authorize]
            public class PublicController : ControllerBase
            {
                [AllowAnonymous]
                [HttpGet("health")]
                public IActionResult Health() => Ok();
            }
            """,
        )
        inventory = _make_inventory(["Controllers/PublicController.cs"])
        profile = _make_profile({"aspnet": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "AllowAnonymous" in surfaces[0].rules
        assert "Authorize" in surfaces[0].rules

    def test_add_authentication_in_program(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Program.cs",
            """\
            var builder = WebApplication.CreateBuilder(args);
            builder.Services.AddAuthentication()
                .AddJwtBearer(options => { options.Authority = "https://auth.example.com"; });
            builder.Services.AddAuthorization();
            """,
        )
        inventory = _make_inventory(["Program.cs"])
        profile = _make_profile({"dotnet-minimal-api": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "service_auth_config" in surfaces[0].rules
        assert any("token_type:jwt" in r for r in surfaces[0].rules)

    def test_require_authorization_minimal_api(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Program.cs",
            """\
            app.MapGet("/secret", () => "hidden")
                .RequireAuthorization();
            """,
        )
        inventory = _make_inventory(["Program.cs"])
        profile = _make_profile({"dotnet-minimal-api": 0.7})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "RequireAuthorization" in surfaces[0].rules

    def test_no_auth_in_controller(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Controllers/HomeController.cs",
            """\
            [ApiController]
            [Route("[controller]")]
            public class HomeController : ControllerBase
            {
                [HttpGet]
                public IActionResult Index() => Ok("Hello");
            }
            """,
        )
        inventory = _make_inventory(["Controllers/HomeController.cs"])
        profile = _make_profile({"aspnet": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert surfaces == []


# ---------------------------------------------------------------------------
# Only runs for detected frameworks
# ---------------------------------------------------------------------------


class TestFrameworkGating:
    """Analyzer only runs extractors for detected stacks."""

    def test_flask_not_run_for_express(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "views/admin.py",
            """\
            @login_required
            def admin():
                pass
            """,
        )
        inventory = _make_inventory(["views/admin.py"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        # Express extractor won't match views/admin.py
        # Flask extractor won't run because flask not detected
        assert surfaces == []

    def test_multiple_frameworks_detected(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "middleware/auth.js",
            "if (req.isAuthenticated()) { next(); }",
        )
        _write_file(
            tmp_path,
            "auth/deps.py",
            """\
            from fastapi import Depends
            def get_current_user(token = Depends(verify_token)):
                pass
            """,
        )
        inventory = _make_inventory(["middleware/auth.js", "auth/deps.py"])
        profile = _make_profile({"express": 0.7, "fastapi": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        names = {s.name for s in surfaces}
        assert "express_auth" in names
        assert "fastapi_auth" in names


# ---------------------------------------------------------------------------
# AuthSurface data model integration
# ---------------------------------------------------------------------------


class TestAuthSurfaceIntegration:
    """Verify produced surfaces conform to the AuthSurface data model."""

    def test_surface_type(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "middleware/auth.js",
            "if (req.isAuthenticated()) { next(); }",
        )
        inventory = _make_inventory(["middleware/auth.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert surfaces[0].surface_type == "auth"

    def test_source_refs_populated(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "middleware/auth.js",
            "if (req.isAuthenticated()) { next(); }",
        )
        inventory = _make_inventory(["middleware/auth.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert len(surfaces[0].source_refs) > 0
        assert surfaces[0].source_refs[0].file_path == "middleware/auth.js"

    def test_to_dict_serializable(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Controllers/ApiController.cs",
            '[Authorize(Roles = "Admin")]',
        )
        inventory = _make_inventory(["Controllers/ApiController.cs"])
        profile = _make_profile({"aspnet": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        d = surfaces[0].to_dict()
        assert d["surface_type"] == "auth"
        assert "Admin" in d["roles"]
        assert isinstance(d["rules"], list)
        assert isinstance(d["source_refs"], list)

    def test_is_auth_surface_instance(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "views/admin.py",
            "@login_required\ndef admin(): pass",
        )
        inventory = _make_inventory(["views/admin.py"])
        profile = _make_profile({"flask": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert isinstance(surfaces[0], AuthSurface)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_unreadable_file(self, tmp_path: Path) -> None:
        """Files that cannot be read are silently skipped."""
        inventory = _make_inventory(["middleware/auth.js"])
        profile = _make_profile({"express": 0.8})
        # Don't create the file — it won't exist on disk
        surfaces = analyze_auth(inventory, profile, tmp_path)
        assert surfaces == []

    def test_empty_file(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "auth/empty.js", "")
        inventory = _make_inventory(["auth/empty.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)
        assert surfaces == []

    def test_multiple_auth_patterns_in_one_file(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "auth/combined.js",
            """\
            const passport = require('passport');
            passport.use(new JwtStrategy(opts, verify));
            passport.authenticate('local');
            if (req.isAuthenticated()) { next(); }
            if (hasRole('admin')) { next(); }
            """,
        )
        inventory = _make_inventory(["auth/combined.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_auth(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert "admin" in surfaces[0].roles
        rules = surfaces[0].rules
        assert any("passport:JwtStrategy" in r for r in rules)
        assert any("passport.authenticate:local" in r for r in rules)
        assert "isAuthenticated" in rules
