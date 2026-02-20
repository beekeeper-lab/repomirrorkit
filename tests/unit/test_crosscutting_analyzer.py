"""Unit tests for the cross-cutting concerns analyzer."""

from __future__ import annotations

import textwrap
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.crosscutting import analyze_crosscutting
from repo_mirror_kit.harvester.analyzers.surfaces import CrosscuttingSurface
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
# No-op when nothing detected
# ---------------------------------------------------------------------------


class TestEmptyRepository:
    """Analyzer returns empty when no cross-cutting concerns found."""

    def test_empty_inventory(self, tmp_path: Path) -> None:
        inventory = _make_inventory([])
        result = analyze_crosscutting(inventory, tmp_path)
        assert result == []

    def test_unrelated_files(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "src/main.py", "print('hello')\n")
        inventory = _make_inventory(["src/main.py"])
        result = analyze_crosscutting(inventory, tmp_path)
        assert result == []


# ---------------------------------------------------------------------------
# Logging detection
# ---------------------------------------------------------------------------


class TestLoggingDetection:
    """Detect logging infrastructure patterns."""

    def test_python_logging(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/logger.py",
            """\
            import logging

            logger = logging.getLogger(__name__)
            logger.info("Starting application")
            """,
        )
        inventory = _make_inventory(["src/logger.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        logging_surfaces = [s for s in result if s.concern_type == "logging"]
        assert len(logging_surfaces) == 1
        assert "python:logging" in logging_surfaces[0].description
        assert "src/logger.py" in logging_surfaces[0].affected_files

    def test_python_structlog(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/log_config.py",
            """\
            import structlog

            structlog.configure(
                processors=[structlog.dev.ConsoleRenderer()],
            )
            """,
        )
        inventory = _make_inventory(["src/log_config.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        logging_surfaces = [s for s in result if s.concern_type == "logging"]
        assert len(logging_surfaces) == 1
        assert "python:structlog" in logging_surfaces[0].description

    def test_node_winston(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/logger.ts",
            """\
            import winston from 'winston';
            const logger = winston.createLogger({
                level: 'info',
                transports: [new winston.transports.Console()],
            });
            """,
        )
        inventory = _make_inventory(["src/logger.ts"])
        result = analyze_crosscutting(inventory, tmp_path)

        logging_surfaces = [s for s in result if s.concern_type == "logging"]
        assert len(logging_surfaces) == 1
        assert "node:winston" in logging_surfaces[0].description

    def test_node_pino(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/logger.js",
            """\
            const pino = require('pino');
            const logger = pino({ level: 'info' });
            """,
        )
        inventory = _make_inventory(["src/logger.js"])
        result = analyze_crosscutting(inventory, tmp_path)

        logging_surfaces = [s for s in result if s.concern_type == "logging"]
        assert len(logging_surfaces) == 1
        assert "node:pino" in logging_surfaces[0].description

    def test_dotnet_serilog(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/Logging.cs",
            """\
            using Serilog;

            Log.Logger = new LoggerConfiguration()
                .WriteTo.Console()
                .CreateLogger();
            """,
        )
        inventory = _make_inventory(["src/Logging.cs"])
        result = analyze_crosscutting(inventory, tmp_path)

        logging_surfaces = [s for s in result if s.concern_type == "logging"]
        assert len(logging_surfaces) == 1
        assert "dotnet:Serilog" in logging_surfaces[0].description

    def test_dotnet_ilogger(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/Service.cs",
            """\
            public class MyService
            {
                private readonly ILogger<MyService> _logger;
                public MyService(ILogger<MyService> logger) { _logger = logger; }
            }
            """,
        )
        inventory = _make_inventory(["src/Service.cs"])
        result = analyze_crosscutting(inventory, tmp_path)

        logging_surfaces = [s for s in result if s.concern_type == "logging"]
        assert len(logging_surfaces) == 1
        assert "dotnet:ILogger" in logging_surfaces[0].description

    def test_multiple_logging_patterns(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/app.py",
            """\
            import logging
            import structlog

            structlog.configure()
            logger = logging.getLogger(__name__)
            """,
        )
        inventory = _make_inventory(["src/app.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        logging_surfaces = [s for s in result if s.concern_type == "logging"]
        assert len(logging_surfaces) == 1
        desc = logging_surfaces[0].description
        assert "python:logging" in desc
        assert "python:structlog" in desc

    def test_python_loguru(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/log_setup.py",
            """\
            from loguru import logger

            logger.add("file.log", rotation="500 MB")
            """,
        )
        inventory = _make_inventory(["src/log_setup.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        logging_surfaces = [s for s in result if s.concern_type == "logging"]
        assert len(logging_surfaces) == 1
        assert "python:loguru" in logging_surfaces[0].description


# ---------------------------------------------------------------------------
# Error handling detection
# ---------------------------------------------------------------------------


class TestErrorHandlingDetection:
    """Detect error handling patterns."""

    def test_react_error_boundary(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/ErrorBoundary.tsx",
            """\
            import React from 'react';

            class ErrorBoundary extends React.Component {
                componentDidCatch(error, errorInfo) {
                    console.error(error, errorInfo);
                }
                render() { return this.props.children; }
            }
            """,
        )
        inventory = _make_inventory(["src/ErrorBoundary.tsx"])
        result = analyze_crosscutting(inventory, tmp_path)

        error_surfaces = [s for s in result if s.concern_type == "error-handling"]
        assert len(error_surfaces) == 1
        assert "react:ErrorBoundary" in error_surfaces[0].description

    def test_express_error_middleware(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/middleware/error.ts",
            """\
            app.use(function(err, req, res, next) {
                console.error(err.stack);
                res.status(500).send('Something broke!');
            });
            """,
        )
        inventory = _make_inventory(["src/middleware/error.ts"])
        result = analyze_crosscutting(inventory, tmp_path)

        error_surfaces = [s for s in result if s.concern_type == "error-handling"]
        assert len(error_surfaces) == 1
        assert "express:errorMiddleware" in error_surfaces[0].description

    def test_node_uncaught_exception(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/error-handler.ts",
            """\
            process.on('uncaughtException', (err) => {
                console.error('Uncaught:', err);
                process.exit(1);
            });
            process.on('unhandledRejection', (reason) => {
                console.error('Unhandled rejection:', reason);
            });
            """,
        )
        inventory = _make_inventory(["src/error-handler.ts"])
        result = analyze_crosscutting(inventory, tmp_path)

        error_surfaces = [s for s in result if s.concern_type == "error-handling"]
        assert len(error_surfaces) == 1
        assert "node:uncaughtException" in error_surfaces[0].description

    def test_python_custom_exception(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/exceptions.py",
            """\
            class AppError(Exception):
                pass

            class NotFoundError(Exception):
                pass
            """,
        )
        inventory = _make_inventory(["src/exceptions.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        error_surfaces = [s for s in result if s.concern_type == "error-handling"]
        assert len(error_surfaces) == 1
        assert "python:custom_exception" in error_surfaces[0].description

    def test_python_sys_excepthook(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/handler.py",
            """\
            import sys

            def custom_hook(exc_type, exc_value, exc_tb):
                pass

            sys.excepthook = custom_hook
            """,
        )
        inventory = _make_inventory(["src/handler.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        error_surfaces = [s for s in result if s.concern_type == "error-handling"]
        assert len(error_surfaces) == 1
        assert "python:sys.excepthook" in error_surfaces[0].description

    def test_dotnet_exception_filter(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/Filters/GlobalExceptionFilter.cs",
            """\
            public class GlobalExceptionFilter : IExceptionFilter
            {
                public void OnException(ExceptionContext context)
                {
                    context.Result = new StatusCodeResult(500);
                }
            }
            """,
        )
        inventory = _make_inventory(["src/Filters/GlobalExceptionFilter.cs"])
        result = analyze_crosscutting(inventory, tmp_path)

        error_surfaces = [s for s in result if s.concern_type == "error-handling"]
        assert len(error_surfaces) == 1
        assert "dotnet:GlobalExceptionFilter" in error_surfaces[0].description

    def test_nestjs_exception_filter(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/filters/http-exception.filter.ts",
            """\
            @Catch(HttpException)
            export class HttpExceptionFilter implements ExceptionFilter {
                catch(exception: HttpException, host: ArgumentsHost) {
                    const ctx = host.switchToHttp();
                }
            }
            """,
        )
        inventory = _make_inventory(["src/filters/http-exception.filter.ts"])
        result = analyze_crosscutting(inventory, tmp_path)

        error_surfaces = [s for s in result if s.concern_type == "error-handling"]
        assert len(error_surfaces) == 1
        assert "nestjs:ExceptionFilter" in error_surfaces[0].description

    def test_js_custom_error_class(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/errors.ts",
            """\
            class NotFoundError extends Error {
                constructor(message: string) {
                    super(message);
                    this.name = 'NotFoundError';
                }
            }
            """,
        )
        inventory = _make_inventory(["src/errors.ts"])
        result = analyze_crosscutting(inventory, tmp_path)

        error_surfaces = [s for s in result if s.concern_type == "error-handling"]
        assert len(error_surfaces) == 1
        assert "js:customError" in error_surfaces[0].description

    def test_python_error_handler_decorator(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/error_handler.py",
            """\
            @app.errorhandler(404)
            def not_found(error):
                return {"error": "Not found"}, 404
            """,
        )
        inventory = _make_inventory(["src/error_handler.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        error_surfaces = [s for s in result if s.concern_type == "error-handling"]
        assert len(error_surfaces) == 1
        assert "python:error_handler" in error_surfaces[0].description


# ---------------------------------------------------------------------------
# Telemetry / Observability detection
# ---------------------------------------------------------------------------


class TestTelemetryDetection:
    """Detect observability and telemetry patterns."""

    def test_opentelemetry(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/telemetry.ts",
            """\
            import { NodeSDK } from '@opentelemetry/sdk-node';
            const sdk = new NodeSDK({});
            sdk.start();
            """,
        )
        inventory = _make_inventory(["src/telemetry.ts"])
        result = analyze_crosscutting(inventory, tmp_path)

        telemetry_surfaces = [s for s in result if s.concern_type == "telemetry"]
        assert len(telemetry_surfaces) == 1
        assert "opentelemetry" in telemetry_surfaces[0].description

    def test_prometheus(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/metrics.py",
            """\
            from prometheus_client import Counter, start_http_server

            requests_total = Counter('requests_total', 'Total requests')
            """,
        )
        inventory = _make_inventory(["src/metrics.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        telemetry_surfaces = [s for s in result if s.concern_type == "telemetry"]
        assert len(telemetry_surfaces) == 1
        assert "prometheus" in telemetry_surfaces[0].description

    def test_sentry(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/monitoring.ts",
            """\
            import * as Sentry from '@sentry/node';
            Sentry.init({ dsn: 'https://example.com' });
            """,
        )
        inventory = _make_inventory(["src/monitoring.ts"])
        result = analyze_crosscutting(inventory, tmp_path)

        telemetry_surfaces = [s for s in result if s.concern_type == "telemetry"]
        assert len(telemetry_surfaces) == 1
        assert "sentry" in telemetry_surfaces[0].description

    def test_datadog(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/tracing.js",
            """\
            const tracer = require('dd-trace').init();
            """,
        )
        inventory = _make_inventory(["src/tracing.js"])
        result = analyze_crosscutting(inventory, tmp_path)

        telemetry_surfaces = [s for s in result if s.concern_type == "telemetry"]
        assert len(telemetry_surfaces) == 1
        assert "datadog" in telemetry_surfaces[0].description

    def test_health_check_endpoint(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/health.ts",
            """\
            app.get('/health', (req, res) => {
                res.status(200).json({ status: 'ok' });
            });
            """,
        )
        inventory = _make_inventory(["src/health.ts"])
        result = analyze_crosscutting(inventory, tmp_path)

        telemetry_surfaces = [s for s in result if s.concern_type == "telemetry"]
        assert len(telemetry_surfaces) == 1
        assert "health_check" in telemetry_surfaces[0].description

    def test_dotnet_health_checks(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/Health.cs",
            """\
            builder.Services.AddHealthChecks();
            app.MapHealthChecks("/health");
            """,
        )
        inventory = _make_inventory(["src/Health.cs"])
        result = analyze_crosscutting(inventory, tmp_path)

        telemetry_surfaces = [s for s in result if s.concern_type == "telemetry"]
        assert len(telemetry_surfaces) == 1
        assert "dotnet:HealthChecks" in telemetry_surfaces[0].description

    def test_newrelic(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/instrument.js",
            """\
            require('newrelic');
            """,
        )
        inventory = _make_inventory(["src/instrument.js"])
        result = analyze_crosscutting(inventory, tmp_path)

        telemetry_surfaces = [s for s in result if s.concern_type == "telemetry"]
        assert len(telemetry_surfaces) == 1
        assert "newrelic" in telemetry_surfaces[0].description

    def test_application_insights(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/Telemetry.cs",
            """\
            var client = new TelemetryClient();
            client.TrackEvent("PageView");
            """,
        )
        inventory = _make_inventory(["src/Telemetry.cs"])
        result = analyze_crosscutting(inventory, tmp_path)

        telemetry_surfaces = [s for s in result if s.concern_type == "telemetry"]
        assert len(telemetry_surfaces) == 1
        assert "appinsights" in telemetry_surfaces[0].description


# ---------------------------------------------------------------------------
# Background job detection
# ---------------------------------------------------------------------------


class TestJobsDetection:
    """Detect background job and worker patterns."""

    def test_node_bull(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/queues/email.ts",
            """\
            import Bull from 'bull';
            const emailQueue = new Bull('email');
            emailQueue.process(async (job) => {
                await sendEmail(job.data);
            });
            """,
        )
        inventory = _make_inventory(["src/queues/email.ts"])
        result = analyze_crosscutting(inventory, tmp_path)

        job_surfaces = [s for s in result if s.concern_type == "jobs"]
        assert len(job_surfaces) == 1
        assert "node:bull" in job_surfaces[0].description

    def test_python_celery(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/tasks/worker.py",
            """\
            from celery import Celery

            app = Celery('tasks', broker='redis://localhost:6379/0')

            @app.task
            def send_email(to, subject, body):
                pass
            """,
        )
        inventory = _make_inventory(["src/tasks/worker.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        job_surfaces = [s for s in result if s.concern_type == "jobs"]
        assert len(job_surfaces) == 1
        assert "python:celery" in job_surfaces[0].description

    def test_python_celery_shared_task(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/tasks/process.py",
            """\
            from celery import shared_task

            @shared_task
            def process_data(data_id):
                pass
            """,
        )
        inventory = _make_inventory(["src/tasks/process.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        job_surfaces = [s for s in result if s.concern_type == "jobs"]
        assert len(job_surfaces) == 1
        assert "python:celery" in job_surfaces[0].description

    def test_dotnet_background_service(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/Workers/CleanupWorker.cs",
            """\
            public class CleanupWorker : BackgroundService
            {
                protected override async Task ExecuteAsync(CancellationToken token)
                {
                    while (!token.IsCancellationRequested) { await Task.Delay(1000); }
                }
            }
            """,
        )
        inventory = _make_inventory(["src/Workers/CleanupWorker.cs"])
        result = analyze_crosscutting(inventory, tmp_path)

        job_surfaces = [s for s in result if s.concern_type == "jobs"]
        assert len(job_surfaces) == 1
        assert "dotnet:BackgroundService" in job_surfaces[0].description

    def test_dotnet_hangfire(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/Jobs/Setup.cs",
            """\
            using Hangfire;

            RecurringJob.AddOrUpdate(() => Console.WriteLine("Hello"), Cron.Daily);
            """,
        )
        inventory = _make_inventory(["src/Jobs/Setup.cs"])
        result = analyze_crosscutting(inventory, tmp_path)

        job_surfaces = [s for s in result if s.concern_type == "jobs"]
        assert len(job_surfaces) == 1
        assert "dotnet:Hangfire" in job_surfaces[0].description

    def test_ruby_sidekiq(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "app/workers/email_worker.rb",
            """\
            class EmailWorker
                include Sidekiq::Worker
                def perform(email_id)
                    # send email
                end
            end
            """,
        )
        inventory = _make_inventory(["app/workers/email_worker.rb"])
        result = analyze_crosscutting(inventory, tmp_path)

        job_surfaces = [s for s in result if s.concern_type == "jobs"]
        assert len(job_surfaces) == 1
        assert "ruby:sidekiq" in job_surfaces[0].description

    def test_node_cron(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/scheduler.ts",
            """\
            import cron from 'node-cron';
            cron.schedule('0 0 * * *', () => { cleanup(); });
            """,
        )
        inventory = _make_inventory(["src/scheduler.ts"])
        result = analyze_crosscutting(inventory, tmp_path)

        job_surfaces = [s for s in result if s.concern_type == "jobs"]
        assert len(job_surfaces) == 1
        assert "node:node-cron" in job_surfaces[0].description

    def test_procfile_worker(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Procfile",
            """\
            web: gunicorn app:app
            worker: celery -A tasks worker
            """,
        )
        inventory = _make_inventory(["Procfile"])
        result = analyze_crosscutting(inventory, tmp_path)

        job_surfaces = [s for s in result if s.concern_type == "jobs"]
        assert len(job_surfaces) == 1
        assert "procfile:worker" in job_surfaces[0].description

    def test_python_apscheduler(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/scheduler.py",
            """\
            from apscheduler.schedulers.background import BackgroundScheduler

            scheduler = BackgroundScheduler()
            scheduler.add_job(my_func, 'interval', minutes=5)
            """,
        )
        inventory = _make_inventory(["src/scheduler.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        job_surfaces = [s for s in result if s.concern_type == "jobs"]
        assert len(job_surfaces) == 1
        assert "python:apscheduler" in job_surfaces[0].description


# ---------------------------------------------------------------------------
# Deployment detection
# ---------------------------------------------------------------------------


class TestDeploymentDetection:
    """Detect deployment configuration patterns."""

    def test_dockerfile(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Dockerfile",
            """\
            FROM python:3.12-slim
            WORKDIR /app
            COPY . .
            RUN pip install -r requirements.txt
            CMD ["python", "main.py"]
            """,
        )
        inventory = _make_inventory(["Dockerfile"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        assert "docker:dockerfile" in deploy_surfaces[0].description
        assert "Dockerfile" in deploy_surfaces[0].affected_files

    def test_docker_compose(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "docker-compose.yml",
            """\
            version: '3'
            services:
              web:
                build: .
                ports:
                  - "8000:8000"
            """,
        )
        inventory = _make_inventory(["docker-compose.yml"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        assert "docker:compose" in deploy_surfaces[0].description

    def test_kubernetes_manifest(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "k8s/deployment.yaml",
            """\
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: my-app
            spec:
              replicas: 3
            """,
        )
        inventory = _make_inventory(["k8s/deployment.yaml"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        assert "k8s:manifest" in deploy_surfaces[0].description
        assert "k8s:deployment" in deploy_surfaces[0].description

    def test_kubernetes_service(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "k8s/service.yaml",
            """\
            apiVersion: v1
            kind: Service
            metadata:
              name: my-service
            spec:
              type: LoadBalancer
            """,
        )
        inventory = _make_inventory(["k8s/service.yaml"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        assert "k8s:service" in deploy_surfaces[0].description

    def test_github_actions(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".github/workflows/ci.yml",
            """\
            name: CI
            on: [push, pull_request]
            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4
            """,
        )
        inventory = _make_inventory([".github/workflows/ci.yml"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        assert "ci:github-actions" in deploy_surfaces[0].description

    def test_gitlab_ci(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".gitlab-ci.yml",
            """\
            stages:
              - build
              - test
            build:
              script: make build
            """,
        )
        inventory = _make_inventory([".gitlab-ci.yml"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        assert "ci:gitlab-ci" in deploy_surfaces[0].description

    def test_jenkinsfile(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Jenkinsfile",
            """\
            pipeline {
                agent any
                stages {
                    stage('Build') { steps { sh 'make' } }
                }
            }
            """,
        )
        inventory = _make_inventory(["Jenkinsfile"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        assert "ci:jenkins" in deploy_surfaces[0].description

    def test_terraform(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "infra/main.tf",
            """\
            resource "aws_instance" "web" {
              ami           = "ami-12345"
              instance_type = "t2.micro"
            }
            """,
        )
        inventory = _make_inventory(["infra/main.tf"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        assert "iac:terraform" in deploy_surfaces[0].description

    def test_vercel_config(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "vercel.json",
            '{"framework": "nextjs"}',
        )
        inventory = _make_inventory(["vercel.json"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        assert "platform:vercel" in deploy_surfaces[0].description

    def test_helm_chart(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Chart.yaml",
            """\
            apiVersion: v2
            name: my-chart
            version: 0.1.0
            """,
        )
        inventory = _make_inventory(["Chart.yaml"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        assert "k8s:helm" in deploy_surfaces[0].description

    def test_multistage_dockerfile(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Dockerfile",
            """\
            FROM node:18 AS builder
            WORKDIR /app
            COPY . .
            RUN npm run build

            FROM node:18-slim
            COPY --from=builder /app/dist ./dist
            CMD ["node", "dist/main.js"]
            """,
        )
        inventory = _make_inventory(["Dockerfile"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        assert "docker:dockerfile" in deploy_surfaces[0].description
        assert "docker:multistage" in deploy_surfaces[0].description

    def test_multiple_ci_platforms(self, tmp_path: Path) -> None:
        _write_file(tmp_path, ".github/workflows/ci.yml", "name: CI\non: [push]")
        _write_file(tmp_path, ".gitlab-ci.yml", "stages:\n  - test")
        inventory = _make_inventory(
            [
                ".github/workflows/ci.yml",
                ".gitlab-ci.yml",
            ]
        )
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        desc = deploy_surfaces[0].description
        assert "ci:github-actions" in desc
        assert "ci:gitlab-ci" in desc

    def test_fly_toml(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "fly.toml",
            """\
            app = "my-app"
            [build]
              builder = "heroku/buildpacks:20"
            """,
        )
        inventory = _make_inventory(["fly.toml"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy_surfaces = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy_surfaces) == 1
        assert "platform:fly" in deploy_surfaces[0].description


# ---------------------------------------------------------------------------
# CrosscuttingSurface data model integration
# ---------------------------------------------------------------------------


class TestCrosscuttingSurfaceIntegration:
    """Verify produced surfaces conform to the CrosscuttingSurface data model."""

    def test_surface_type(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "Dockerfile", "FROM python:3.12\nCMD ['python']")
        inventory = _make_inventory(["Dockerfile"])
        result = analyze_crosscutting(inventory, tmp_path)

        assert len(result) >= 1
        deploy = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy) == 1
        assert deploy[0].surface_type == "crosscutting"

    def test_source_refs_populated(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path, "src/logger.py", "import logging\nlogging.getLogger(__name__)"
        )
        inventory = _make_inventory(["src/logger.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        logging_surfaces = [s for s in result if s.concern_type == "logging"]
        assert len(logging_surfaces) == 1
        assert len(logging_surfaces[0].source_refs) > 0
        assert logging_surfaces[0].source_refs[0].file_path == "src/logger.py"

    def test_to_dict_serializable(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "Dockerfile", "FROM node:18\nCMD ['node']")
        inventory = _make_inventory(["Dockerfile"])
        result = analyze_crosscutting(inventory, tmp_path)

        deploy = [s for s in result if s.concern_type == "deployment"]
        assert len(deploy) == 1
        d = deploy[0].to_dict()
        assert d["surface_type"] == "crosscutting"
        assert d["concern_type"] == "deployment"
        assert isinstance(d["description"], str)
        assert isinstance(d["affected_files"], list)
        assert isinstance(d["source_refs"], list)

    def test_is_crosscutting_surface_instance(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path, "src/log.py", "import structlog\nlogger = structlog.get_logger()"
        )
        inventory = _make_inventory(["src/log.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        logging_surfaces = [s for s in result if s.concern_type == "logging"]
        assert len(logging_surfaces) == 1
        assert isinstance(logging_surfaces[0], CrosscuttingSurface)

    def test_concern_type_values(self, tmp_path: Path) -> None:
        """Verify concern_type uses expected categories."""
        _write_file(tmp_path, "src/log.py", "import logging\nlogging.getLogger()")
        _write_file(
            tmp_path,
            "src/errors.py",
            "class AppError(Exception):\n    pass",
        )
        _write_file(
            tmp_path,
            "src/metrics.py",
            "from prometheus_client import Counter",
        )
        _write_file(
            tmp_path,
            "src/tasks/worker.py",
            "from celery import Celery",
        )
        _write_file(tmp_path, "Dockerfile", "FROM python:3.12")
        inventory = _make_inventory(
            [
                "src/log.py",
                "src/errors.py",
                "src/metrics.py",
                "src/tasks/worker.py",
                "Dockerfile",
            ]
        )
        result = analyze_crosscutting(inventory, tmp_path)

        concern_types = {s.concern_type for s in result}
        assert "logging" in concern_types
        assert "error-handling" in concern_types
        assert "telemetry" in concern_types
        assert "jobs" in concern_types
        assert "deployment" in concern_types


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_unreadable_file(self, tmp_path: Path) -> None:
        """Files that cannot be read are silently skipped."""
        inventory = _make_inventory(["src/logger.py"])
        # Don't create the file — it won't exist on disk
        result = analyze_crosscutting(inventory, tmp_path)
        assert result == []

    def test_empty_file(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "src/logger.py", "")
        inventory = _make_inventory(["src/logger.py"])
        result = analyze_crosscutting(inventory, tmp_path)
        assert result == []

    def test_multiple_concerns_detected(self, tmp_path: Path) -> None:
        """Multiple concern types can be detected from a single repo."""
        _write_file(
            tmp_path,
            "src/app.py",
            """\
            import logging
            logger = logging.getLogger(__name__)
            """,
        )
        _write_file(tmp_path, "Dockerfile", "FROM python:3.12\nCMD ['python']")
        inventory = _make_inventory(["src/app.py", "Dockerfile"])
        result = analyze_crosscutting(inventory, tmp_path)

        concern_types = {s.concern_type for s in result}
        assert "logging" in concern_types
        assert "deployment" in concern_types

    def test_affected_files_deduplicated(self, tmp_path: Path) -> None:
        """A file matching multiple patterns appears only once in affected_files."""
        _write_file(
            tmp_path,
            "src/logger.py",
            """\
            import logging
            import structlog

            logger = logging.getLogger(__name__)
            structlog.configure()
            """,
        )
        inventory = _make_inventory(["src/logger.py"])
        result = analyze_crosscutting(inventory, tmp_path)

        logging_surfaces = [s for s in result if s.concern_type == "logging"]
        assert len(logging_surfaces) == 1
        # The file should only appear once even though it matched multiple patterns
        assert logging_surfaces[0].affected_files.count("src/logger.py") == 1
