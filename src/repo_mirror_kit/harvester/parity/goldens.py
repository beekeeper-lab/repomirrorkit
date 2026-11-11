"""Golden request/response capture and replay (BEAN-077).

Golden format (``schema_version`` 1.0)::

    {
      "schema_version": "1.0",
      "name": "shop-orders",
      "captured_from": "parity-flask",
      "message_fields": ["error", "message", "detail"],
      "interactions": [
        {"name": "create ok",
         "request":  {"method": "POST", "path": "/api/orders",
                      "headers": {"X-API-Key": "demo-key"}, "json": {...}},
         "response": {"status": 201, "json": {...}}}
      ]
    }

A *script* (``<name>.script.json``) lists requests to drive; ``"auth": true``
adds the credential headers given to :func:`capture`/:func:`replay`.

Comparison: an interaction passes when the status is equal and the JSON bodies
match field-by-field. Fields named in ``message_fields`` (human-readable error
text) only need to be present and string-typed for the *tolerant* score; the
*strict* score demands exact text. Volatile fields (``volatile_fields``, e.g.
timestamps) are ignored entirely.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.parity.server import http_call

logger = structlog.get_logger()

GOLDEN_VERSION = "1.0"
DEFAULT_MESSAGE_FIELDS = ("error", "message", "detail")


class GoldenError(Exception):
    """Malformed script or golden file."""


def load_script(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("requests"), list):
        raise GoldenError(f"{path}: script must be an object with a 'requests' list")
    return data


def _build(
    item: dict[str, Any], auth_headers: dict[str, str], defaults: dict[str, Any]
) -> dict[str, Any]:
    headers = {**defaults.get("headers", {}), **item.get("headers", {})}
    if item.get("auth"):
        headers.update(auth_headers)
    request: dict[str, Any] = {
        "method": str(item["method"]).upper(),
        "path": str(item["path"]),
        "headers": headers,
    }
    if "json" in item:
        request["json"] = item["json"]
    return request


def capture(
    base_url: str,
    script: dict[str, Any],
    auth_headers: dict[str, str],
    captured_from: str = "",
    volatile_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Run *script* against a live app and return the golden document."""
    defaults = script.get("defaults", {})
    interactions: list[dict[str, Any]] = []
    for item in script["requests"]:
        request = _build(item, auth_headers, defaults)
        status, parsed, raw = http_call(
            base_url,
            request["method"],
            request["path"],
            request["headers"],
            request.get("json"),
        )
        response: dict[str, Any] = {"status": status}
        if parsed is not None:
            response["json"] = parsed
        elif raw.strip():
            response["text"] = raw[:500]
        interactions.append(
            {
                "name": item.get("name", request["path"]),
                "request": request,
                "response": response,
            }
        )
    return {
        "schema_version": GOLDEN_VERSION,
        "name": script.get("name", ""),
        "captured_from": captured_from,
        "message_fields": list(DEFAULT_MESSAGE_FIELDS),
        "volatile_fields": list(volatile_fields),
        "interactions": interactions,
    }


def _strip_volatile(value: Any, volatile: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            k: _strip_volatile(v, volatile)
            for k, v in value.items()
            if k not in volatile
        }
    if isinstance(value, list):
        return [_strip_volatile(v, volatile) for v in value]
    return value


def _leaf_diff(
    expected: Any, actual: Any, message_fields: set[str], tolerant: bool, path: str = ""
) -> tuple[int, int, list[str]]:
    """(matching leaves, total expected leaves, mismatch descriptions)."""
    if isinstance(expected, dict):
        total = matched = 0
        notes: list[str] = []
        for key, exp_val in expected.items():
            sub_actual = actual.get(key) if isinstance(actual, dict) else None
            present = isinstance(actual, dict) and key in actual
            if not present:
                n = _count_leaves(exp_val)
                total += n
                notes.append(f"{path}/{key}: missing")
                continue
            m, t, sub = _leaf_diff(
                exp_val, sub_actual, message_fields, tolerant, f"{path}/{key}"
            )
            matched += m
            total += t
            notes += sub
        return matched, total, notes
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return 0, max(_count_leaves(expected), 1), [f"{path}: expected list"]
        matched = total = 0
        notes = []
        for i, exp_val in enumerate(expected):
            if i < len(actual):
                m, t, sub = _leaf_diff(
                    exp_val, actual[i], message_fields, tolerant, f"{path}[{i}]"
                )
            else:
                m, t, sub = 0, _count_leaves(exp_val), [f"{path}[{i}]: missing"]
            matched += m
            total += t
            notes += sub
        extra = max(0, len(actual) - len(expected))
        if extra:
            total += extra
            notes.append(f"{path}: {extra} unexpected extra item(s)")
        return matched, max(total, 1), notes
    # scalar leaf
    key = path.rsplit("/", 1)[-1].split("[")[0]
    if tolerant and key in message_fields and isinstance(expected, str):
        ok = isinstance(actual, str) and bool(actual)
    else:
        ok = expected == actual
    return (
        (1, 1, []) if ok else (0, 1, [f"{path}: expected {expected!r}, got {actual!r}"])
    )


def _count_leaves(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_count_leaves(v) for v in value.values()) or 1
    if isinstance(value, list):
        return sum(_count_leaves(v) for v in value) or 1
    return 1


@dataclass
class InteractionResult:
    name: str
    passed: bool
    strict_passed: bool
    status_expected: int
    status_actual: int
    field_matches: int = 0
    field_total: int = 0
    notes: list[str] = field(default_factory=list)


@dataclass
class ReplayResult:
    results: list[InteractionResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def strict_passed(self) -> int:
        return sum(1 for r in self.results if r.strict_passed)

    @property
    def pass_rate(self) -> float | None:
        return self.passed / self.total if self.total else None

    @property
    def strict_rate(self) -> float | None:
        return self.strict_passed / self.total if self.total else None

    @property
    def field_match_rate(self) -> float | None:
        total = sum(r.field_total for r in self.results)
        return sum(r.field_matches for r in self.results) / total if total else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "interactions": self.total,
            "passed": self.passed,
            "strict_passed": self.strict_passed,
            "pass_rate": self.pass_rate,
            "strict_rate": self.strict_rate,
            "field_match_rate": self.field_match_rate,
            "failures": [
                {
                    "name": r.name,
                    "status_expected": r.status_expected,
                    "status_actual": r.status_actual,
                    "notes": r.notes[:6],
                }
                for r in self.results
                if not r.passed
            ],
        }


def replay(base_url: str, golden: dict[str, Any]) -> ReplayResult:
    """Replay *golden* against a live app and score each interaction."""
    if golden.get("schema_version") != GOLDEN_VERSION:
        raise GoldenError(
            f"unsupported golden schema_version {golden.get('schema_version')!r}"
        )
    message_fields = set(golden.get("message_fields", DEFAULT_MESSAGE_FIELDS))
    volatile = set(golden.get("volatile_fields", []))
    results: list[InteractionResult] = []
    for item in golden["interactions"]:
        req = item["request"]
        status, parsed, _raw = http_call(
            base_url,
            req["method"],
            req["path"],
            req.get("headers", {}),
            req.get("json"),
        )
        exp = item["response"]
        exp_json = _strip_volatile(exp.get("json"), volatile) if "json" in exp else None
        act_json = _strip_volatile(parsed, volatile)
        notes: list[str] = []
        matched = total = 0
        body_ok = True
        strict_ok = True
        if exp_json is not None:
            m, t, notes = _leaf_diff(exp_json, act_json, message_fields, tolerant=True)
            ms, ts, _ = _leaf_diff(exp_json, act_json, message_fields, tolerant=False)
            matched, total = m, t
            body_ok = m == t
            strict_ok = ms == ts
            if (
                isinstance(exp_json, list)
                and isinstance(act_json, list)
                and len(act_json) != len(exp_json)
            ):
                body_ok = strict_ok = False
        elif "text" in exp:
            body_ok = strict_ok = True  # non-JSON bodies are not compared
        status_ok = status == exp["status"]
        if not status_ok:
            notes.insert(0, f"status expected {exp['status']}, got {status}")
        results.append(
            InteractionResult(
                name=str(item.get("name", req["path"])),
                passed=status_ok and body_ok,
                strict_passed=status_ok and strict_ok,
                status_expected=int(exp["status"]),
                status_actual=status,
                field_matches=matched if status_ok else 0,
                field_total=total,
                notes=notes,
            )
        )
    return ReplayResult(results)
