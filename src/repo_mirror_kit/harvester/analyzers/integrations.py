"""External integration analyzer for service-to-service communication.

Discovers outbound HTTP calls, gRPC stubs, message queue producers/consumers,
webhook handlers, and SDK client instantiations.  Produces
``IntegrationSurface`` objects with integration type, target service,
protocol, and data exchange hints.

Supported integration types:
- REST client (fetch, axios, requests, httpx, aiohttp)
- gRPC (stubs, channels, service clients)
- Message queue (RabbitMQ/AMQP, Kafka, Redis pub/sub, SQS)
- Webhook (route handlers with "webhook" in path)
- SDK (AWS SDK, Stripe, Twilio, SendGrid, etc.)

Uses heuristic-based extraction (pattern matching, not full AST) per spec v1.
"""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import IntegrationSurface, SourceRef
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# Extensions scanned for integration patterns.
_JS_TS_EXTENSIONS: frozenset[str] = frozenset({".js", ".jsx", ".ts", ".tsx"})
_PY_EXTENSIONS: frozenset[str] = frozenset({".py"})
_ALL_EXTENSIONS: frozenset[str] = _JS_TS_EXTENSIONS | _PY_EXTENSIONS

_MAX_FILE_READ_BYTES: int = 512_000  # 500 KB limit for heuristic scanning.

# ---------------------------------------------------------------------------
# REST client patterns
# ---------------------------------------------------------------------------

# JS: fetch('url'), fetch(`url`)
_FETCH_RE = re.compile(
    r"""fetch\s*\(\s*[`"']([^`"']+)[`"']""",
)

# JS: axios.get/post/put/delete/patch('url')
_AXIOS_RE = re.compile(
    r"""axios\.(\w+)\s*\(\s*[`"']([^`"']+)[`"']""",
)

# Python: requests.get/post/put/delete/patch('url')
_REQUESTS_RE = re.compile(
    r"""requests\.(\w+)\s*\(\s*["']([^"']+)["']""",
)

# Python: httpx.get/post/put/delete/patch or httpx.AsyncClient
_HTTPX_RE = re.compile(
    r"""httpx\.(?:(\w+)\s*\(\s*["']([^"']+)["']|(?:AsyncClient|Client)\s*\()""",
)

# Python: aiohttp.ClientSession
_AIOHTTP_SESSION_RE = re.compile(
    r"""aiohttp\.ClientSession\s*\(""",
)

# aiohttp session.get/post etc.
_AIOHTTP_CALL_RE = re.compile(
    r"""session\.(\w+)\s*\(\s*["']([^"']+)["']""",
)

# ---------------------------------------------------------------------------
# gRPC patterns
# ---------------------------------------------------------------------------

# Python: grpc.insecure_channel / grpc.secure_channel
_GRPC_CHANNEL_RE = re.compile(
    r"""grpc\.(?:insecure_channel|secure_channel)\s*\(\s*["']([^"']+)["']""",
)

# JS/Python: *Stub( or *Client( pattern for gRPC generated stubs
_GRPC_STUB_RE = re.compile(
    r"""(\w+(?:Stub|ServiceClient))\s*\(""",
)

# Proto import hints
_GRPC_IMPORT_RE = re.compile(
    r"""(?:from\s+\S+_pb2(?:_grpc)?\s+import|require\s*\(\s*["'][^"']*_grpc_pb["']\))""",
)

# ---------------------------------------------------------------------------
# Message queue patterns
# ---------------------------------------------------------------------------

# RabbitMQ / AMQP: pika, amqplib, amqp
_RABBITMQ_RE = re.compile(
    r"""(?:pika\.(?:BlockingConnection|SelectConnection|URLParameters)|amqp\.Connection)\s*\(""",
)

# Kafka: KafkaProducer, KafkaConsumer, Kafka() from kafkajs
_KAFKA_RE = re.compile(
    r"""(?:KafkaProducer|KafkaConsumer|new\s+Kafka)\s*\(""",
)

# Redis pub/sub: redis.publish, redis.subscribe, pubsub()
_REDIS_PUBSUB_RE = re.compile(
    r"""(?:redis\w*\.(?:publish|subscribe)|\.pubsub\s*\()""",
)

# AWS SQS: sqs.send_message, sqs.receive_message, SQSClient
_SQS_RE = re.compile(
    r"""(?:sqs\.(?:send_message|receive_message|delete_message)|SQSClient\s*\(|["']sqs["'])""",
)

# ---------------------------------------------------------------------------
# Webhook patterns
# ---------------------------------------------------------------------------

# Route paths containing "webhook"
_WEBHOOK_ROUTE_RE = re.compile(
    r"""(?:path|route|url)\s*[=(]\s*["']([^"']*webhook[^"']*)["']""",
    re.IGNORECASE,
)

# Express/FastAPI-style: app.post('/webhook/...')
_WEBHOOK_HANDLER_RE = re.compile(
    r"""(?:app|router)\.\w+\s*\(\s*["']([^"']*webhook[^"']*)["']""",
    re.IGNORECASE,
)

# Django urls.py: path('webhook/...', handler)
_WEBHOOK_DJANGO_RE = re.compile(
    r"""path\s*\(\s*["']([^"']*webhook[^"']*)["']""",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# SDK client patterns
# ---------------------------------------------------------------------------

# AWS SDK: boto3.client('s3'), boto3.resource('dynamodb')
_AWS_BOTO3_RE = re.compile(
    r"""boto3\.(?:client|resource)\s*\(\s*["'](\w+)["']""",
)

# AWS JS SDK: new S3Client, new DynamoDBClient, etc.
_AWS_JS_SDK_RE = re.compile(
    r"""new\s+(S3Client|DynamoDBClient|LambdaClient|SNSClient|SQSClient|SecretsManagerClient)\s*\(""",
)

# Stripe: stripe.Stripe(), new Stripe()
_STRIPE_RE = re.compile(
    r"""(?:stripe\.Stripe|new\s+Stripe)\s*\(""",
)

# Twilio: twilio.rest.Client(), new Twilio()
_TWILIO_RE = re.compile(
    r"""(?:twilio\.rest\.Client|new\s+(?:Twilio|twilio\.Twilio))\s*\(""",
)

# SendGrid: SendGridAPIClient, @sendgrid/mail
_SENDGRID_RE = re.compile(
    r"""(?:SendGridAPIClient\s*\(|from\s+["']@sendgrid)""",
)

# Generic SDK patterns: new SomeServiceClient(
_GENERIC_SDK_RE = re.compile(
    r"""new\s+(\w+(?:Client|SDK|Service))\s*\(""",
)


def analyze_integrations(
    inventory: InventoryResult,
    profile: StackProfile,
    workdir: Path | None = None,
) -> list[IntegrationSurface]:
    """Discover external service integrations across the repository.

    Scans source files for HTTP client calls, gRPC stubs, message queue
    connections, webhook handlers, and SDK client instantiations.

    Args:
        inventory: The scanned file inventory.
        profile: Detection results identifying which stacks are present.
        workdir: Repository working directory for reading file contents.

    Returns:
        A list of ``IntegrationSurface`` objects, one per discovered
        integration point.
    """
    if workdir is None:
        logger.debug("integrations_skipped", reason="no_workdir")
        return []

    surfaces: list[IntegrationSurface] = []

    for entry in inventory.files:
        if entry.extension not in _ALL_EXTENSIONS:
            continue

        content = _read_file_safe(workdir / entry.path)
        if content is None:
            continue

        surfaces.extend(_scan_rest_clients(content, entry.path))
        surfaces.extend(_scan_grpc(content, entry.path))
        surfaces.extend(_scan_queues(content, entry.path))
        surfaces.extend(_scan_webhooks(content, entry.path))
        surfaces.extend(_scan_sdks(content, entry.path))

    logger.info("integration_analysis_complete", total_surfaces=len(surfaces))
    return surfaces


# ---------------------------------------------------------------------------
# Integration-type scanners
# ---------------------------------------------------------------------------


def _scan_rest_clients(content: str, file_path: str) -> list[IntegrationSurface]:
    """Scan content for HTTP client calls (fetch, axios, requests, httpx, aiohttp).

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``IntegrationSurface`` objects for REST client calls.
    """
    surfaces: list[IntegrationSurface] = []

    # fetch()
    for match in _FETCH_RE.finditer(content):
        url = match.group(1)
        surfaces.append(
            IntegrationSurface(
                name=f"rest_client:fetch:{file_path}",
                integration_type="rest_client",
                target_service=_extract_host(url),
                protocol="http",
                data_exchanged=[url],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # axios
    for match in _AXIOS_RE.finditer(content):
        method = match.group(1)
        url = match.group(2)
        surfaces.append(
            IntegrationSurface(
                name=f"rest_client:axios:{method}:{file_path}",
                integration_type="rest_client",
                target_service=_extract_host(url),
                protocol="http",
                data_exchanged=[url],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # requests (Python)
    for match in _REQUESTS_RE.finditer(content):
        method = match.group(1)
        url = match.group(2)
        # Skip common false positives from non-HTTP method names.
        if method not in {"get", "post", "put", "delete", "patch", "head", "options"}:
            continue
        surfaces.append(
            IntegrationSurface(
                name=f"rest_client:requests:{method}:{file_path}",
                integration_type="rest_client",
                target_service=_extract_host(url),
                protocol="http",
                data_exchanged=[url],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # httpx (Python)
    for match in _HTTPX_RE.finditer(content):
        method = match.group(1) or "client"
        url = match.group(2) or ""
        surfaces.append(
            IntegrationSurface(
                name=f"rest_client:httpx:{method}:{file_path}",
                integration_type="rest_client",
                target_service=_extract_host(url) if url else "unknown",
                protocol="http",
                data_exchanged=[url] if url else [],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # aiohttp
    if _AIOHTTP_SESSION_RE.search(content):
        for match in _AIOHTTP_CALL_RE.finditer(content):
            method = match.group(1)
            url = match.group(2)
            if method not in {
                "get", "post", "put", "delete", "patch", "head", "options",
            }:
                continue
            surfaces.append(
                IntegrationSurface(
                    name=f"rest_client:aiohttp:{method}:{file_path}",
                    integration_type="rest_client",
                    target_service=_extract_host(url),
                    protocol="http",
                    data_exchanged=[url],
                    source_refs=[
                        SourceRef(
                            file_path=file_path,
                            start_line=_line_number(content, match.start()),
                        )
                    ],
                )
            )

    return surfaces


def _scan_grpc(content: str, file_path: str) -> list[IntegrationSurface]:
    """Scan content for gRPC channel and stub patterns.

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``IntegrationSurface`` objects for gRPC integrations.
    """
    surfaces: list[IntegrationSurface] = []

    # gRPC channels
    for match in _GRPC_CHANNEL_RE.finditer(content):
        target = match.group(1)
        surfaces.append(
            IntegrationSurface(
                name=f"grpc:channel:{target}",
                integration_type="grpc",
                target_service=target,
                protocol="grpc",
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # gRPC stubs / service clients (only if proto imports are present)
    if _GRPC_IMPORT_RE.search(content):
        for match in _GRPC_STUB_RE.finditer(content):
            stub_name = match.group(1)
            surfaces.append(
                IntegrationSurface(
                    name=f"grpc:stub:{stub_name}",
                    integration_type="grpc",
                    target_service=stub_name,
                    protocol="grpc",
                    source_refs=[
                        SourceRef(
                            file_path=file_path,
                            start_line=_line_number(content, match.start()),
                        )
                    ],
                )
            )

    return surfaces


def _scan_queues(content: str, file_path: str) -> list[IntegrationSurface]:
    """Scan content for message queue producer/consumer patterns.

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``IntegrationSurface`` objects for queue integrations.
    """
    surfaces: list[IntegrationSurface] = []

    # RabbitMQ / AMQP
    for match in _RABBITMQ_RE.finditer(content):
        surfaces.append(
            IntegrationSurface(
                name=f"queue:rabbitmq:{file_path}",
                integration_type="queue",
                target_service="rabbitmq",
                protocol="amqp",
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # Kafka
    for match in _KAFKA_RE.finditer(content):
        surfaces.append(
            IntegrationSurface(
                name=f"queue:kafka:{file_path}",
                integration_type="queue",
                target_service="kafka",
                protocol="kafka",
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # Redis pub/sub
    for match in _REDIS_PUBSUB_RE.finditer(content):
        surfaces.append(
            IntegrationSurface(
                name=f"queue:redis_pubsub:{file_path}",
                integration_type="queue",
                target_service="redis",
                protocol="redis_pubsub",
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # AWS SQS
    for match in _SQS_RE.finditer(content):
        surfaces.append(
            IntegrationSurface(
                name=f"queue:sqs:{file_path}",
                integration_type="queue",
                target_service="aws_sqs",
                protocol="sqs",
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    return surfaces


def _scan_webhooks(content: str, file_path: str) -> list[IntegrationSurface]:
    """Scan content for webhook handler route definitions.

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``IntegrationSurface`` objects for webhook integrations.
    """
    surfaces: list[IntegrationSurface] = []
    seen_paths: set[str] = set()

    for pattern in (_WEBHOOK_ROUTE_RE, _WEBHOOK_HANDLER_RE, _WEBHOOK_DJANGO_RE):
        for match in pattern.finditer(content):
            webhook_path = match.group(1)
            if webhook_path in seen_paths:
                continue
            seen_paths.add(webhook_path)
            surfaces.append(
                IntegrationSurface(
                    name=f"webhook:{webhook_path}",
                    integration_type="webhook",
                    target_service="inbound",
                    protocol="http",
                    data_exchanged=[webhook_path],
                    source_refs=[
                        SourceRef(
                            file_path=file_path,
                            start_line=_line_number(content, match.start()),
                        )
                    ],
                )
            )

    return surfaces


def _scan_sdks(content: str, file_path: str) -> list[IntegrationSurface]:
    """Scan content for SDK client instantiations.

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``IntegrationSurface`` objects for SDK integrations.
    """
    surfaces: list[IntegrationSurface] = []

    # AWS boto3
    for match in _AWS_BOTO3_RE.finditer(content):
        service = match.group(1)
        surfaces.append(
            IntegrationSurface(
                name=f"sdk:aws:{service}",
                integration_type="sdk",
                target_service=f"aws_{service}",
                protocol="aws_sdk",
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # AWS JS SDK v3
    for match in _AWS_JS_SDK_RE.finditer(content):
        client_name = match.group(1)
        surfaces.append(
            IntegrationSurface(
                name=f"sdk:aws:{client_name}",
                integration_type="sdk",
                target_service=f"aws_{client_name}",
                protocol="aws_sdk",
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # Stripe
    for match in _STRIPE_RE.finditer(content):
        surfaces.append(
            IntegrationSurface(
                name=f"sdk:stripe:{file_path}",
                integration_type="sdk",
                target_service="stripe",
                protocol="http",
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # Twilio
    for match in _TWILIO_RE.finditer(content):
        surfaces.append(
            IntegrationSurface(
                name=f"sdk:twilio:{file_path}",
                integration_type="sdk",
                target_service="twilio",
                protocol="http",
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # SendGrid
    for match in _SENDGRID_RE.finditer(content):
        surfaces.append(
            IntegrationSurface(
                name=f"sdk:sendgrid:{file_path}",
                integration_type="sdk",
                target_service="sendgrid",
                protocol="http",
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # Generic SDK clients (only if no specific SDK was detected for this file)
    if not surfaces:
        for match in _GENERIC_SDK_RE.finditer(content):
            client_name = match.group(1)
            # Skip common false positives.
            if client_name in {"HttpClient", "WebClient", "TestClient"}:
                continue
            surfaces.append(
                IntegrationSurface(
                    name=f"sdk:{client_name}:{file_path}",
                    integration_type="sdk",
                    target_service=client_name,
                    protocol="unknown",
                    source_refs=[
                        SourceRef(
                            file_path=file_path,
                            start_line=_line_number(content, match.start()),
                        )
                    ],
                )
            )

    return surfaces


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_host(url: str) -> str:
    """Extract a host or service hint from a URL string.

    Handles full URLs (``https://api.example.com/v1/users``) and
    relative paths (``/api/users``).  Template variables and
    environment variable references are returned as-is.

    Args:
        url: The URL or path string.

    Returns:
        The extracted host portion, or ``"relative"`` for path-only URLs.
    """
    if url.startswith(("http://", "https://")):
        # Strip scheme, then take everything up to the first slash.
        without_scheme = url.split("//", maxsplit=1)[-1]
        host = without_scheme.split("/", maxsplit=1)[0]
        return host
    if url.startswith("/"):
        return "relative"
    # Template or variable references.
    return url.split("/", maxsplit=1)[0] if "/" in url else url


def _read_file_safe(file_path: Path) -> str | None:
    """Read a file's text content safely, returning None on failure.

    Args:
        file_path: Absolute path to the file to read.

    Returns:
        The file content as a string, or None if reading failed.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        if len(content) > _MAX_FILE_READ_BYTES:
            logger.debug(
                "integration_file_too_large",
                path=str(file_path),
                size=len(content),
            )
            return None
        return content
    except OSError:
        logger.debug("integration_file_read_failed", path=str(file_path))
        return None


def _line_number(content: str, char_offset: int) -> int:
    """Calculate the 1-based line number for a character offset.

    Args:
        content: The full file content.
        char_offset: Zero-based character position.

    Returns:
        The 1-based line number.
    """
    return content[:char_offset].count("\n") + 1
