"""Unit tests for the external integrations analyzer."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.integrations import analyze_integrations
from repo_mirror_kit.harvester.analyzers.surfaces import IntegrationSurface
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory(files: list[FileEntry]) -> InventoryResult:
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=sum(f.size for f in files),
        total_skipped=0,
    )


def _make_profile() -> StackProfile:
    return StackProfile(stacks={}, evidence={}, signals=[])


def _write_file(tmp_path: Path, rel_path: str, content: str) -> FileEntry:
    full_path = tmp_path / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    ext = ""
    dot = rel_path.rfind(".")
    if dot != -1:
        ext = rel_path[dot:]
    return FileEntry(
        path=rel_path, size=len(content), extension=ext, hash="abc123", category="source"
    )


# ---------------------------------------------------------------------------
# Empty / no matches
# ---------------------------------------------------------------------------


class TestEmptyResults:
    """Verify analyzer returns empty list when no integration patterns are present."""

    def test_no_integration_patterns(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/utils.ts",
            "export function add(a: number, b: number) { return a + b; }\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        assert result == []

    def test_no_workdir_returns_empty(self) -> None:
        entry = FileEntry(
            path="src/api.ts", size=100, extension=".ts", hash="abc123", category="source"
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=None)

        assert result == []

    def test_non_source_files_skipped(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "data/config.yaml",
            "key: value\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        assert result == []


# ---------------------------------------------------------------------------
# HTTP client detection: fetch
# ---------------------------------------------------------------------------


class TestFetchDetection:
    """Tests for fetch() call detection."""

    def test_fetch_with_url_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/api/client.ts",
            """\
async function getUsers() {
  const response = await fetch('https://api.example.com/users');
  return response.json();
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        rest_surfaces = [s for s in result if s.integration_type == "rest_client"]
        assert len(rest_surfaces) >= 1
        surface = rest_surfaces[0]
        assert isinstance(surface, IntegrationSurface)
        assert surface.surface_type == "integration"
        assert surface.protocol == "http"
        assert surface.target_service == "api.example.com"
        assert "https://api.example.com/users" in surface.data_exchanged

    def test_fetch_with_relative_path(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/api/client.ts",
            "const res = await fetch('/api/data');\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        rest_surfaces = [s for s in result if s.integration_type == "rest_client"]
        assert len(rest_surfaces) >= 1
        assert rest_surfaces[0].target_service == "relative"


# ---------------------------------------------------------------------------
# HTTP client detection: axios
# ---------------------------------------------------------------------------


class TestAxiosDetection:
    """Tests for axios HTTP call detection."""

    def test_axios_get_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/api/users.ts",
            """\
import axios from 'axios';

const response = await axios.get('https://api.example.com/users');
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        rest_surfaces = [s for s in result if s.integration_type == "rest_client"]
        assert len(rest_surfaces) >= 1
        surface = rest_surfaces[0]
        assert surface.protocol == "http"
        assert surface.target_service == "api.example.com"

    def test_axios_post_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/api/submit.ts",
            "const res = await axios.post('https://api.example.com/submit');\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        rest_surfaces = [s for s in result if s.integration_type == "rest_client"]
        assert len(rest_surfaces) >= 1


# ---------------------------------------------------------------------------
# HTTP client detection: requests (Python)
# ---------------------------------------------------------------------------


class TestRequestsDetection:
    """Tests for Python requests library detection."""

    def test_requests_get_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/client.py",
            """\
import requests

response = requests.get('https://api.example.com/users')
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        rest_surfaces = [s for s in result if s.integration_type == "rest_client"]
        assert len(rest_surfaces) >= 1
        surface = rest_surfaces[0]
        assert surface.protocol == "http"
        assert surface.target_service == "api.example.com"

    def test_requests_post_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/client.py",
            "response = requests.post('https://api.example.com/data')\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        rest_surfaces = [s for s in result if s.integration_type == "rest_client"]
        assert len(rest_surfaces) >= 1

    def test_requests_non_http_method_skipped(self, tmp_path: Path) -> None:
        """Non-HTTP methods on requests should be skipped."""
        entry = _write_file(
            tmp_path,
            "src/client.py",
            "requests.session('https://example.com')\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        rest_surfaces = [s for s in result if s.integration_type == "rest_client"]
        assert rest_surfaces == []


# ---------------------------------------------------------------------------
# HTTP client detection: httpx
# ---------------------------------------------------------------------------


class TestHttpxDetection:
    """Tests for Python httpx library detection."""

    def test_httpx_get_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/client.py",
            "response = httpx.get('https://api.example.com/data')\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        rest_surfaces = [s for s in result if s.integration_type == "rest_client"]
        assert len(rest_surfaces) >= 1
        assert rest_surfaces[0].protocol == "http"

    def test_httpx_async_client_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/client.py",
            "client = httpx.AsyncClient()\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        rest_surfaces = [s for s in result if s.integration_type == "rest_client"]
        assert len(rest_surfaces) >= 1


# ---------------------------------------------------------------------------
# Webhook detection
# ---------------------------------------------------------------------------


class TestWebhookDetection:
    """Tests for webhook handler detection."""

    def test_webhook_route_path_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/routes.py",
            """\
path('/webhook/stripe', stripe_webhook_handler)
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        webhook_surfaces = [s for s in result if s.integration_type == "webhook"]
        assert len(webhook_surfaces) >= 1
        surface = webhook_surfaces[0]
        assert surface.target_service == "inbound"
        assert surface.protocol == "http"
        assert "/webhook/stripe" in surface.data_exchanged[0]

    def test_express_webhook_handler_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/webhooks.ts",
            """\
app.post('/webhook/github', handleGithubWebhook);
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        webhook_surfaces = [s for s in result if s.integration_type == "webhook"]
        assert len(webhook_surfaces) >= 1

    def test_django_webhook_path_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "urls.py",
            """\
from django.urls import path

urlpatterns = [
    path('webhook/payments', payment_webhook),
]
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        webhook_surfaces = [s for s in result if s.integration_type == "webhook"]
        assert len(webhook_surfaces) >= 1

    def test_webhook_deduplication(self, tmp_path: Path) -> None:
        """Duplicate webhook paths in the same file are deduplicated."""
        entry = _write_file(
            tmp_path,
            "src/webhooks.py",
            """\
path('/webhook/stripe', stripe_handler)
route = '/webhook/stripe'
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        webhook_surfaces = [s for s in result if s.integration_type == "webhook"]
        webhook_paths = [s.data_exchanged[0] for s in webhook_surfaces]
        # Verify the same path doesn't appear twice.
        assert len(webhook_paths) == len(set(webhook_paths))


# ---------------------------------------------------------------------------
# Message queue detection
# ---------------------------------------------------------------------------


class TestMessageQueueDetection:
    """Tests for message queue connection detection."""

    def test_kafka_producer_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/producer.py",
            """\
from kafka import KafkaProducer

producer = KafkaProducer(bootstrap_servers='localhost:9092')
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        queue_surfaces = [s for s in result if s.integration_type == "queue"]
        assert len(queue_surfaces) >= 1
        kafka_surfaces = [s for s in queue_surfaces if s.target_service == "kafka"]
        assert len(kafka_surfaces) >= 1
        assert kafka_surfaces[0].protocol == "kafka"

    def test_kafka_consumer_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/consumer.py",
            "consumer = KafkaConsumer('topic')\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        queue_surfaces = [s for s in result if s.target_service == "kafka"]
        assert len(queue_surfaces) >= 1

    def test_rabbitmq_pika_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/queue.py",
            """\
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        queue_surfaces = [s for s in result if s.target_service == "rabbitmq"]
        assert len(queue_surfaces) >= 1
        assert queue_surfaces[0].protocol == "amqp"

    def test_redis_pubsub_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/pubsub.py",
            """\
import redis

r = redis.Redis()
r.pubsub()
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        queue_surfaces = [s for s in result if s.target_service == "redis"]
        assert len(queue_surfaces) >= 1
        assert queue_surfaces[0].protocol == "redis_pubsub"

    def test_sqs_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/queue.py",
            "sqs.send_message(QueueUrl=queue_url, MessageBody=msg)\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        queue_surfaces = [s for s in result if s.target_service == "aws_sqs"]
        assert len(queue_surfaces) >= 1
        assert queue_surfaces[0].protocol == "sqs"


# ---------------------------------------------------------------------------
# gRPC detection
# ---------------------------------------------------------------------------


class TestGrpcDetection:
    """Tests for gRPC channel and stub detection."""

    def test_grpc_channel_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/client.py",
            """\
import grpc

channel = grpc.insecure_channel('localhost:50051')
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        grpc_surfaces = [s for s in result if s.integration_type == "grpc"]
        assert len(grpc_surfaces) >= 1
        assert grpc_surfaces[0].target_service == "localhost:50051"
        assert grpc_surfaces[0].protocol == "grpc"

    def test_grpc_stub_with_proto_import_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/client.py",
            """\
from myservice_pb2_grpc import MyServiceStub

stub = MyServiceStub(channel)
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        grpc_surfaces = [s for s in result if s.integration_type == "grpc"]
        assert len(grpc_surfaces) >= 1
        stub_surfaces = [s for s in grpc_surfaces if "MyServiceStub" in s.target_service]
        assert len(stub_surfaces) >= 1


# ---------------------------------------------------------------------------
# SDK detection
# ---------------------------------------------------------------------------


class TestSdkDetection:
    """Tests for SDK client instantiation detection."""

    def test_boto3_client_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/aws.py",
            """\
import boto3

s3 = boto3.client('s3')
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        sdk_surfaces = [s for s in result if s.integration_type == "sdk"]
        assert len(sdk_surfaces) >= 1
        s3_surfaces = [s for s in sdk_surfaces if s.target_service == "aws_s3"]
        assert len(s3_surfaces) >= 1
        assert s3_surfaces[0].protocol == "aws_sdk"

    def test_stripe_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/payments.py",
            """\
import stripe

client = stripe.Stripe('sk_test_123')
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        sdk_surfaces = [s for s in result if s.target_service == "stripe"]
        assert len(sdk_surfaces) >= 1

    def test_twilio_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/sms.py",
            """\
from twilio.rest import Client

client = twilio.rest.Client(account_sid, auth_token)
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        sdk_surfaces = [s for s in result if s.target_service == "twilio"]
        assert len(sdk_surfaces) >= 1

    def test_aws_js_sdk_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/aws.ts",
            """\
import { S3Client } from '@aws-sdk/client-s3';

const client = new S3Client({ region: 'us-east-1' });
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        sdk_surfaces = [s for s in result if s.integration_type == "sdk"]
        assert len(sdk_surfaces) >= 1
        assert sdk_surfaces[0].target_service == "aws_S3Client"


# ---------------------------------------------------------------------------
# Source refs and surface type
# ---------------------------------------------------------------------------


class TestSourceRefsAndSurfaceType:
    """Verify source_refs are populated and surface_type is correct."""

    def test_source_refs_populated(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/api/client.ts",
            "const res = await fetch('https://api.example.com/data');\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) >= 1
        for surface in result:
            assert len(surface.source_refs) == 1
            assert surface.source_refs[0].file_path == "src/api/client.ts"
            assert surface.source_refs[0].start_line is not None
            assert surface.source_refs[0].start_line > 0

    def test_all_surfaces_are_integration_type(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/client.py",
            "response = requests.get('https://api.example.com/users')\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        for surface in result:
            assert isinstance(surface, IntegrationSurface)
            assert surface.surface_type == "integration"

    def test_integration_type_and_protocol_fields(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/client.ts",
            "const res = await fetch('https://api.example.com/v1/users');\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) >= 1
        surface = result[0]
        assert surface.integration_type == "rest_client"
        assert surface.target_service == "api.example.com"
        assert surface.protocol == "http"


# ---------------------------------------------------------------------------
# Multiple integration types
# ---------------------------------------------------------------------------


class TestMultipleIntegrations:
    """Tests for repositories using multiple integration patterns."""

    def test_rest_and_queue_in_same_repo(self, tmp_path: Path) -> None:
        entry1 = _write_file(
            tmp_path,
            "src/api.py",
            "response = requests.get('https://api.example.com/users')\n",
        )
        entry2 = _write_file(
            tmp_path,
            "src/queue.py",
            "producer = KafkaProducer(bootstrap_servers='localhost:9092')\n",
        )
        inventory = _make_inventory([entry1, entry2])
        result = analyze_integrations(inventory, _make_profile(), workdir=tmp_path)

        types = {s.integration_type for s in result}
        assert "rest_client" in types
        assert "queue" in types
