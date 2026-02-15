"""Auth & security analyzer.

Extracts authentication and authorization patterns from source files,
producing AuthSurface objects with roles, permissions, protected endpoints,
and token/session type information.

Supports: Express/Passport, FastAPI, Flask, Next.js/NextAuth, NestJS,
and ASP.NET Core authorization patterns.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import AuthSurface, SourceRef
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_MAX_FILE_SIZE = 512_000  # Skip files larger than 512 KB
_MAX_FILES_TO_SCAN = 200  # Cap per framework to bound runtime

# ---------------------------------------------------------------------------
# Express / Node auth patterns
# ---------------------------------------------------------------------------

_EXPRESS_AUTH_FILE_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)(?:middleware|auth|passport|guards?)/.*\.[jt]sx?$"
)

_PASSPORT_USE_RE: re.Pattern[str] = re.compile(
    r"passport\.use\s*\(\s*(?:new\s+)?(\w+Strategy)",
)
_PASSPORT_AUTHENTICATE_RE: re.Pattern[str] = re.compile(
    r"passport\.authenticate\s*\(\s*['\"](\w+)['\"]",
)
_IS_AUTHENTICATED_RE: re.Pattern[str] = re.compile(
    r"\bisAuthenticated\b",
)
_EXPRESS_MIDDLEWARE_RE: re.Pattern[str] = re.compile(
    r"(?:app|router)\.\s*(?:use|get|post|put|patch|delete)\s*\("
    r"[^)]*(?:auth|protect|require|verify|guard)\w*",
    re.IGNORECASE,
)
_EXPRESS_ROLE_RE: re.Pattern[str] = re.compile(
    r"(?:role|roles|hasRole|requireRole)\s*\(\s*['\"](\w+)['\"]",
    re.IGNORECASE,
)
_EXPRESS_JWT_RE: re.Pattern[str] = re.compile(
    r"\b(?:jwt|jsonwebtoken|JwtStrategy|express-jwt)\b",
    re.IGNORECASE,
)
_EXPRESS_SESSION_RE: re.Pattern[str] = re.compile(
    r"\b(?:express-session|cookie-session|req\.session)\b",
)

# ---------------------------------------------------------------------------
# FastAPI auth patterns
# ---------------------------------------------------------------------------

_FASTAPI_AUTH_FILE_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)(?:dependencies|deps|auth|security|routers)/.*\.py$"
)

_FASTAPI_DEPENDS_AUTH_RE: re.Pattern[str] = re.compile(
    r"Depends\s*\(\s*(\w*(?:auth|user|token|current|verify|login)\w*)",
    re.IGNORECASE,
)
_FASTAPI_SECURITY_RE: re.Pattern[str] = re.compile(
    r"\b(?:Security|OAuth2PasswordBearer|HTTPBearer|APIKeyHeader|HTTPBasic)\s*\(",
)
_FASTAPI_ROLE_RE: re.Pattern[str] = re.compile(
    r"(?:role|roles|scopes?)\s*[=:]\s*\[([^\]]+)\]",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Flask auth patterns
# ---------------------------------------------------------------------------

_FLASK_AUTH_FILE_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)(?:auth|views|blueprints|decorators)/.*\.py$"
    r"|(?:^|/)app\.py$"
)

_FLASK_LOGIN_REQUIRED_RE: re.Pattern[str] = re.compile(
    r"@login_required\b",
)
_FLASK_ROLES_REQUIRED_RE: re.Pattern[str] = re.compile(
    r"@roles_required\s*\(\s*(['\"].*?['\"](?:\s*,\s*['\"].*?['\"])*)\s*\)",
)
_FLASK_ROLE_EXTRACT_RE: re.Pattern[str] = re.compile(
    r"['\"](\w+)['\"]",
)
_FLASK_CURRENT_USER_RE: re.Pattern[str] = re.compile(
    r"\bcurrent_user\b",
)
_FLASK_LOGIN_MANAGER_RE: re.Pattern[str] = re.compile(
    r"\bLoginManager\s*\(",
)

# ---------------------------------------------------------------------------
# Next.js / NextAuth patterns
# ---------------------------------------------------------------------------

_NEXTJS_AUTH_FILE_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)middleware\.[jt]sx?$"
    r"|(?:^|/)(?:pages|app)/api/auth/.*\.[jt]sx?$"
    r"|(?:^|/)auth\.config\.[jt]sx?$"
    r"|(?:^|/)(?:lib|utils)/auth\.[jt]sx?$"
)

_NEXTAUTH_RE: re.Pattern[str] = re.compile(
    r"\b(?:NextAuth|getServerSession|useSession|getSession)\b",
)
_NEXTJS_MIDDLEWARE_AUTH_RE: re.Pattern[str] = re.compile(
    r"(?:matcher|config)\s*.*(?:protected|auth|login|api)",
    re.IGNORECASE,
)
_NEXTJS_GSSP_AUTH_RE: re.Pattern[str] = re.compile(
    r"getServerSideProps.*(?:session|auth|token|user)",
    re.IGNORECASE | re.DOTALL,
)
_NEXTJS_PROVIDER_RE: re.Pattern[str] = re.compile(
    r"providers?\s*:\s*\[([^\]]+)\]",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# NestJS auth patterns
# ---------------------------------------------------------------------------

_NESTJS_AUTH_FILE_RE: re.Pattern[str] = re.compile(
    r"\.guard\.ts$"
    r"|\.strategy\.ts$"
    r"|(?:^|/)auth/.*\.ts$"
)

_NESTJS_USE_GUARDS_RE: re.Pattern[str] = re.compile(
    r"@UseGuards\s*\(\s*(\w+)",
)
_NESTJS_ROLES_RE: re.Pattern[str] = re.compile(
    r"@Roles\s*\(\s*([^)]+)\)",
)
_NESTJS_ROLE_EXTRACT_RE: re.Pattern[str] = re.compile(
    r"['\"](\w+)['\"]",
)
_NESTJS_AUTH_GUARD_RE: re.Pattern[str] = re.compile(
    r"\b(?:AuthGuard|JwtAuthGuard|LocalAuthGuard|RolesGuard)\b",
)
_NESTJS_PASSPORT_RE: re.Pattern[str] = re.compile(
    r"\bPassportStrategy\b",
)

# ---------------------------------------------------------------------------
# .NET auth patterns
# ---------------------------------------------------------------------------

_DOTNET_AUTH_FILE_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)(?:Controllers|Authorization|Auth)/.*\.cs$"
    r"|(?:^|/)Program\.cs$"
    r"|(?:^|/)Startup\.cs$"
)

_DOTNET_AUTHORIZE_RE: re.Pattern[str] = re.compile(
    r"\[Authorize(?:\s*\(([^)]*)\))?\]",
)
_DOTNET_ALLOW_ANON_RE: re.Pattern[str] = re.compile(
    r"\[AllowAnonymous\]",
)
_DOTNET_ROLES_RE: re.Pattern[str] = re.compile(
    r'Roles\s*=\s*"([^"]+)"',
)
_DOTNET_POLICY_RE: re.Pattern[str] = re.compile(
    r'Policy\s*=\s*"([^"]+)"',
)
_DOTNET_ADD_AUTH_RE: re.Pattern[str] = re.compile(
    r"\.Add(?:Authentication|Authorization|JwtBearer|Cookie)\s*\(",
)
_DOTNET_REQUIRE_AUTH_RE: re.Pattern[str] = re.compile(
    r"\.RequireAuthorization\s*\(",
)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


def analyze_auth(
    inventory: InventoryResult,
    profile: StackProfile,
    workdir: Path,
) -> list[AuthSurface]:
    """Extract auth patterns from a repository.

    Examines files matching detected frameworks and extracts authentication
    and authorization surfaces including roles, permissions, protected
    endpoints, and token types.

    Args:
        inventory: The scanned file inventory.
        profile: Stack detection profile indicating which frameworks are present.
        workdir: Root directory of the repository checkout.

    Returns:
        A list of AuthSurface objects found in the repository.
    """
    detected = set(profile.stacks.keys())
    surfaces: list[AuthSurface] = []

    # Map stack names to extraction functions
    _extractors: list[
        tuple[set[str], Callable[[InventoryResult, Path], list[AuthSurface]]]
    ] = [
        ({"express", "fastify"}, _extract_express_auth),
        ({"fastapi"}, _extract_fastapi_auth),
        ({"flask"}, _extract_flask_auth),
        ({"nextjs"}, _extract_nextjs_auth),
        ({"nestjs"}, _extract_nestjs_auth),
        ({"aspnet", "dotnet-minimal-api"}, _extract_dotnet_auth),
    ]

    for stack_names, extractor in _extractors:
        if detected & stack_names:
            framework = next(iter(detected & stack_names))
            logger.info("auth_analysis_starting", framework=framework)
            results = extractor(inventory, workdir)
            surfaces.extend(results)
            logger.info(
                "auth_analysis_complete",
                framework=framework,
                surfaces_found=len(results),
            )

    logger.info("auth_analysis_total", total_surfaces=len(surfaces))
    return surfaces


def _read_file_safe(path: Path) -> str | None:
    """Read a file's text content, returning None on failure.

    Args:
        path: Absolute path to the file.

    Returns:
        File content as string, or None if unreadable or too large.
    """
    try:
        if path.stat().st_size > _MAX_FILE_SIZE:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _matching_files(
    inventory: InventoryResult,
    pattern: re.Pattern[str],
) -> list[FileEntry]:
    """Return inventory files whose paths match the given regex.

    Args:
        inventory: The file inventory.
        pattern: Regex to match against file paths.

    Returns:
        Matching FileEntry objects, capped at _MAX_FILES_TO_SCAN.
    """
    matches = [f for f in inventory.files if pattern.search(f.path)]
    return matches[:_MAX_FILES_TO_SCAN]


def _detect_token_type(content: str) -> str:
    """Infer the token/session type from file content.

    Args:
        content: Source file text.

    Returns:
        One of 'jwt', 'session', 'cookie', 'oauth2', or '' if unknown.
    """
    lower = content.lower()
    if "jwt" in lower or "jsonwebtoken" in lower or "jwtbearer" in lower:
        return "jwt"
    if "oauth2" in lower or "oauth" in lower:
        return "oauth2"
    if "session" in lower and ("express-session" in lower or "req.session" in lower):
        return "session"
    if "cookie" in lower and ("cookie-session" in lower or "addcookie" in lower):
        return "cookie"
    return ""


# ---------------------------------------------------------------------------
# Express / Node extraction
# ---------------------------------------------------------------------------


def _extract_express_auth(
    inventory: InventoryResult,
    workdir: Path,
) -> list[AuthSurface]:
    """Extract Express/Node auth patterns.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        AuthSurface objects for Express auth patterns.
    """
    files = _matching_files(inventory, _EXPRESS_AUTH_FILE_RE)
    if not files:
        return []

    surfaces: list[AuthSurface] = []
    all_roles: list[str] = []
    all_rules: list[str] = []
    all_endpoints: list[str] = []
    evidence_refs: list[SourceRef] = []
    token_type = ""

    for entry in files:
        path = workdir / entry.path
        content = _read_file_safe(path)
        if content is None:
            continue

        found_auth = False

        # Passport strategies
        for m in _PASSPORT_USE_RE.finditer(content):
            all_rules.append(f"passport:{m.group(1)}")
            found_auth = True

        for m in _PASSPORT_AUTHENTICATE_RE.finditer(content):
            all_rules.append(f"passport.authenticate:{m.group(1)}")
            found_auth = True

        # isAuthenticated checks
        if _IS_AUTHENTICATED_RE.search(content):
            all_rules.append("isAuthenticated")
            found_auth = True

        # Middleware patterns
        if _EXPRESS_MIDDLEWARE_RE.search(content):
            all_rules.append("auth_middleware")
            found_auth = True

        # Role extractions
        for m in _EXPRESS_ROLE_RE.finditer(content):
            role = m.group(1)
            if role not in all_roles:
                all_roles.append(role)
            found_auth = True

        # Token type detection
        if not token_type:
            if _EXPRESS_JWT_RE.search(content):
                token_type = "jwt"  # noqa: S105 — not a password, classifying auth mechanism
            elif _EXPRESS_SESSION_RE.search(content):
                token_type = "session"  # noqa: S105 — not a password, classifying auth mechanism

        if found_auth:
            evidence_refs.append(SourceRef(file_path=entry.path))

    if not evidence_refs:
        return []

    # Deduplicate rules
    unique_rules = list(dict.fromkeys(all_rules))

    surfaces.append(
        AuthSurface(
            name="express_auth",
            roles=all_roles,
            permissions=[],
            rules=unique_rules,
            protected_endpoints=all_endpoints,
            source_refs=evidence_refs,
        )
    )

    if token_type:
        surfaces[0].rules.append(f"token_type:{token_type}")

    return surfaces


# ---------------------------------------------------------------------------
# FastAPI extraction
# ---------------------------------------------------------------------------


def _extract_fastapi_auth(
    inventory: InventoryResult,
    workdir: Path,
) -> list[AuthSurface]:
    """Extract FastAPI auth patterns.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        AuthSurface objects for FastAPI auth patterns.
    """
    files = _matching_files(inventory, _FASTAPI_AUTH_FILE_RE)
    if not files:
        return []

    surfaces: list[AuthSurface] = []
    all_roles: list[str] = []
    all_permissions: list[str] = []
    all_rules: list[str] = []
    evidence_refs: list[SourceRef] = []
    token_type = ""

    for entry in files:
        path = workdir / entry.path
        content = _read_file_safe(path)
        if content is None:
            continue

        found_auth = False

        # Depends() with auth dependencies
        for m in _FASTAPI_DEPENDS_AUTH_RE.finditer(content):
            dep_name = m.group(1)
            all_rules.append(f"Depends:{dep_name}")
            found_auth = True

        # Security schemes
        for m in _FASTAPI_SECURITY_RE.finditer(content):
            scheme = m.group(0).split("(")[0].strip()
            all_rules.append(f"security:{scheme}")
            found_auth = True

        # Roles/scopes
        for m in _FASTAPI_ROLE_RE.finditer(content):
            items = m.group(1)
            for role_m in re.finditer(r"['\"](\w+)['\"]", items):
                val = role_m.group(1)
                if val not in all_roles:
                    all_roles.append(val)
            found_auth = True

        # Token type
        if not token_type:
            token_type = _detect_token_type(content)

        if found_auth:
            evidence_refs.append(SourceRef(file_path=entry.path))

    if not evidence_refs:
        return []

    unique_rules = list(dict.fromkeys(all_rules))

    surfaces.append(
        AuthSurface(
            name="fastapi_auth",
            roles=all_roles,
            permissions=all_permissions,
            rules=unique_rules,
            protected_endpoints=[],
            source_refs=evidence_refs,
        )
    )

    if token_type:
        surfaces[0].rules.append(f"token_type:{token_type}")

    return surfaces


# ---------------------------------------------------------------------------
# Flask extraction
# ---------------------------------------------------------------------------


def _extract_flask_auth(
    inventory: InventoryResult,
    workdir: Path,
) -> list[AuthSurface]:
    """Extract Flask auth patterns.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        AuthSurface objects for Flask auth patterns.
    """
    files = _matching_files(inventory, _FLASK_AUTH_FILE_RE)
    if not files:
        return []

    surfaces: list[AuthSurface] = []
    all_roles: list[str] = []
    all_rules: list[str] = []
    evidence_refs: list[SourceRef] = []

    for entry in files:
        path = workdir / entry.path
        content = _read_file_safe(path)
        if content is None:
            continue

        found_auth = False

        # @login_required
        if _FLASK_LOGIN_REQUIRED_RE.search(content):
            all_rules.append("login_required")
            found_auth = True

        # @roles_required
        for m in _FLASK_ROLES_REQUIRED_RE.finditer(content):
            for role_m in _FLASK_ROLE_EXTRACT_RE.finditer(m.group(1)):
                role = role_m.group(1)
                if role not in all_roles:
                    all_roles.append(role)
            all_rules.append("roles_required")
            found_auth = True

        # current_user usage
        if _FLASK_CURRENT_USER_RE.search(content):
            all_rules.append("current_user")
            found_auth = True

        # LoginManager
        if _FLASK_LOGIN_MANAGER_RE.search(content):
            all_rules.append("flask_login:LoginManager")
            found_auth = True

        if found_auth:
            evidence_refs.append(SourceRef(file_path=entry.path))

    if not evidence_refs:
        return []

    unique_rules = list(dict.fromkeys(all_rules))

    surfaces.append(
        AuthSurface(
            name="flask_auth",
            roles=all_roles,
            permissions=[],
            rules=unique_rules,
            protected_endpoints=[],
            source_refs=evidence_refs,
        )
    )

    return surfaces


# ---------------------------------------------------------------------------
# Next.js / NextAuth extraction
# ---------------------------------------------------------------------------


def _extract_nextjs_auth(
    inventory: InventoryResult,
    workdir: Path,
) -> list[AuthSurface]:
    """Extract Next.js/NextAuth auth patterns.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        AuthSurface objects for Next.js auth patterns.
    """
    files = _matching_files(inventory, _NEXTJS_AUTH_FILE_RE)
    if not files:
        return []

    surfaces: list[AuthSurface] = []
    all_rules: list[str] = []
    all_roles: list[str] = []
    evidence_refs: list[SourceRef] = []

    for entry in files:
        path = workdir / entry.path
        content = _read_file_safe(path)
        if content is None:
            continue

        found_auth = False

        # NextAuth / session usage
        if _NEXTAUTH_RE.search(content):
            all_rules.append("nextauth")
            found_auth = True

        # Middleware auth patterns
        if _NEXTJS_MIDDLEWARE_AUTH_RE.search(content):
            all_rules.append("middleware_auth")
            found_auth = True

        # getServerSideProps auth
        if _NEXTJS_GSSP_AUTH_RE.search(content):
            all_rules.append("getServerSideProps_auth")
            found_auth = True

        # Auth providers
        for m in _NEXTJS_PROVIDER_RE.finditer(content):
            providers_str = m.group(1)
            for provider_m in re.finditer(r"(\w+Provider)", providers_str):
                all_rules.append(f"provider:{provider_m.group(1)}")
            found_auth = True

        if found_auth:
            evidence_refs.append(SourceRef(file_path=entry.path))

    if not evidence_refs:
        return []

    unique_rules = list(dict.fromkeys(all_rules))

    surfaces.append(
        AuthSurface(
            name="nextjs_auth",
            roles=all_roles,
            permissions=[],
            rules=unique_rules,
            protected_endpoints=[],
            source_refs=evidence_refs,
        )
    )

    return surfaces


# ---------------------------------------------------------------------------
# NestJS extraction
# ---------------------------------------------------------------------------


def _extract_nestjs_auth(
    inventory: InventoryResult,
    workdir: Path,
) -> list[AuthSurface]:
    """Extract NestJS auth patterns.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        AuthSurface objects for NestJS auth patterns.
    """
    files = _matching_files(inventory, _NESTJS_AUTH_FILE_RE)
    if not files:
        return []

    surfaces: list[AuthSurface] = []
    all_roles: list[str] = []
    all_rules: list[str] = []
    evidence_refs: list[SourceRef] = []

    for entry in files:
        path = workdir / entry.path
        content = _read_file_safe(path)
        if content is None:
            continue

        found_auth = False

        # @UseGuards
        for m in _NESTJS_USE_GUARDS_RE.finditer(content):
            guard_name = m.group(1)
            all_rules.append(f"UseGuards:{guard_name}")
            found_auth = True

        # @Roles
        for m in _NESTJS_ROLES_RE.finditer(content):
            for role_m in _NESTJS_ROLE_EXTRACT_RE.finditer(m.group(1)):
                role = role_m.group(1)
                if role not in all_roles:
                    all_roles.append(role)
            all_rules.append("Roles")
            found_auth = True

        # AuthGuard / JwtAuthGuard references
        if _NESTJS_AUTH_GUARD_RE.search(content):
            all_rules.append("AuthGuard")
            found_auth = True

        # Passport strategy
        if _NESTJS_PASSPORT_RE.search(content):
            all_rules.append("PassportStrategy")
            found_auth = True

        if found_auth:
            evidence_refs.append(SourceRef(file_path=entry.path))

    if not evidence_refs:
        return []

    unique_rules = list(dict.fromkeys(all_rules))

    surfaces.append(
        AuthSurface(
            name="nestjs_auth",
            roles=all_roles,
            permissions=[],
            rules=unique_rules,
            protected_endpoints=[],
            source_refs=evidence_refs,
        )
    )

    return surfaces


# ---------------------------------------------------------------------------
# .NET extraction
# ---------------------------------------------------------------------------


def _extract_dotnet_auth(
    inventory: InventoryResult,
    workdir: Path,
) -> list[AuthSurface]:
    """Extract ASP.NET authorization patterns.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        AuthSurface objects for .NET auth patterns.
    """
    files = _matching_files(inventory, _DOTNET_AUTH_FILE_RE)
    if not files:
        return []

    surfaces: list[AuthSurface] = []
    all_roles: list[str] = []
    all_permissions: list[str] = []
    all_rules: list[str] = []
    evidence_refs: list[SourceRef] = []
    token_type = ""

    for entry in files:
        path = workdir / entry.path
        content = _read_file_safe(path)
        if content is None:
            continue

        found_auth = False

        # [Authorize] attributes
        for m in _DOTNET_AUTHORIZE_RE.finditer(content):
            all_rules.append("Authorize")
            attr_content = m.group(1) or ""

            # Extract roles
            roles_m = _DOTNET_ROLES_RE.search(attr_content)
            if roles_m:
                for role in roles_m.group(1).split(","):
                    role = role.strip()
                    if role and role not in all_roles:
                        all_roles.append(role)

            # Extract policies
            policy_m = _DOTNET_POLICY_RE.search(attr_content)
            if policy_m:
                policy = policy_m.group(1).strip()
                if policy and policy not in all_permissions:
                    all_permissions.append(policy)

            found_auth = True

        # [AllowAnonymous]
        if _DOTNET_ALLOW_ANON_RE.search(content):
            all_rules.append("AllowAnonymous")
            found_auth = True

        # AddAuthentication / AddAuthorization
        if _DOTNET_ADD_AUTH_RE.search(content):
            all_rules.append("service_auth_config")
            found_auth = True

        # RequireAuthorization
        if _DOTNET_REQUIRE_AUTH_RE.search(content):
            all_rules.append("RequireAuthorization")
            found_auth = True

        # Token type
        if not token_type:
            token_type = _detect_token_type(content)

        if found_auth:
            evidence_refs.append(SourceRef(file_path=entry.path))

    if not evidence_refs:
        return []

    unique_rules = list(dict.fromkeys(all_rules))

    surfaces.append(
        AuthSurface(
            name="dotnet_auth",
            roles=all_roles,
            permissions=all_permissions,
            rules=unique_rules,
            protected_endpoints=[],
            source_refs=evidence_refs,
        )
    )

    if token_type:
        surfaces[0].rules.append(f"token_type:{token_type}")

    return surfaces
