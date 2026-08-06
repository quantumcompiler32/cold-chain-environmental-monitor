#!/usr/bin/env python3
"""Verify the local cold-chain pipeline through its public process boundaries."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "backend" / "e2e_scenarios.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "test-reports"
DEFAULT_BRIDGE_PORT = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    cases = manifest.get("cases")
    if manifest.get("version") != 1 or not isinstance(cases, list) or not cases:
        raise ValueError(f"Invalid E2E scenario manifest: {path}")
    return manifest


def public_environment() -> dict[str, str]:
    """Report non-secret connection settings used by local backend."""
    return {
        "app_env": os.environ.get("APP_ENV", "development"),
        "postgres_host": os.environ.get("POSTGRES_HOST", "localhost"),
        "postgres_port": os.environ.get("POSTGRES_PORT", "5432"),
        "postgres_db": os.environ.get("POSTGRES_DB", "iotdb"),
        "mqtt_broker": os.environ.get("MQTT_BROKER", "localhost"),
        "mqtt_port": os.environ.get("MQTT_PORT", "1883"),
    }


def start_process(command: list[str], *, env: dict[str, str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def http_json(url: str, *, timeout: float = 2.0) -> tuple[int, dict[str, Any]]:
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"error": body}
        return exc.code, payload


def wait_for_bridge(base_url: str, process: subprocess.Popen[str], timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error: str | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"dashboard bridge exited with code {process.returncode}")
        try:
            status, payload = http_json(f"{base_url}/ready")
            if status == 200 and payload.get("ready") is True:
                return payload
            if status == 404:
                legacy_status, legacy_payload = http_json(f"{base_url}/health")
                if legacy_status == 200 and legacy_payload.get("database_connected") is True:
                    return legacy_payload
            last_error = json.dumps(payload, sort_keys=True)
        except (URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
        time.sleep(0.2)
    raise RuntimeError(f"dashboard bridge did not become database-ready: {last_error or 'no response'}")


def read_correlated_events(base_url: str, batch_id: str) -> tuple[int, dict[str, Any]]:
    query = urlencode({"batch": batch_id})
    return http_json(f"{base_url}/api/events?{query}", timeout=5.0)


def generator_supports_run_id(python: str, env: dict[str, str]) -> bool:
    """Keep the verifier usable with older checkouts before run_id was added."""
    result = subprocess.run(
        [python, "-m", "backend.temperature_event_generator", "--help"],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0 and "--run-id" in result.stdout


def event_checks(case: dict[str, Any], events: list[dict[str, Any]], batch_id: str, run_id: str) -> list[dict[str, Any]]:
    """Check observable scenario invariants without recomputing temperatures."""
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "status": "passed" if passed else "failed", "detail": detail})

    expected_count = int(case["count"])
    check("event_count", len(events) == expected_count, f"expected {expected_count}, observed {len(events)}")
    check(
        "correlation_key",
        bool(events) and all(event.get("batch_id") == batch_id for event in events),
        f"all returned events use batch_id={batch_id}",
    )
    if events and any("run_id" in event for event in events):
        check(
            "run_correlation",
            all(event.get("run_id") == run_id for event in events),
            f"all returned events use run_id={run_id}",
        )
    check(
        "top_level_scenario",
        bool(events) and all(event.get("scenario") == case["scenario"] for event in events),
        f"all returned events use scenario={case['scenario']}",
    )

    observed_statuses = sorted({event.get("status") for event in events})
    required_statuses = sorted(case.get("required_statuses", []))
    check("status_contract", all(status in observed_statuses for status in required_statuses), f"required={required_statuses}, observed={observed_statuses}")

    observed_operational = sorted({event.get("operational_status") for event in events})
    required_operational = sorted(case.get("required_operational_statuses", []))
    check("operational_status_contract", all(status in observed_operational for status in required_operational), f"required={required_operational}, observed={observed_operational}")
    acceptable_operational = set(case.get("acceptable_operational_statuses", []))
    if acceptable_operational:
        check("acceptable_operational_statuses", set(observed_operational).issubset(acceptable_operational), f"acceptable={sorted(acceptable_operational)}, observed={observed_operational}")

    observed_alerts = sorted({event.get("rule_alert") for event in events if event.get("rule_alert")})
    required_alerts = sorted(case.get("required_alerts", []))
    check("alert_contract", all(alert in observed_alerts for alert in required_alerts), f"required={required_alerts}, observed={observed_alerts}")

    observed_phases = [event.get("scenario_phase") or event.get("scenario") for event in events]
    required_phases = sorted(case.get("required_phases", []))
    check("phase_contract", all(phase in observed_phases for phase in required_phases), f"required={required_phases}, observed={sorted(set(observed_phases))}")
    if "phase_sequence" in case:
        check("phase_sequence", observed_phases == case["phase_sequence"], f"expected={case['phase_sequence']}, observed={observed_phases}")
    if events and "first_status" in case:
        check("first_status", events[0].get("status") == case["first_status"], f"expected={case['first_status']}, observed={events[0].get('status')}")
    if events and "last_status" in case:
        check("last_status", events[-1].get("status") == case["last_status"], f"expected={case['last_status']}, observed={events[-1].get('status')}")
    return checks


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# End-to-end verification report",
        "",
        f"- Status: **{summary['status'].upper()}**",
        f"- Run ID: `{report['run_id']}`",
        f"- Started: `{report['started_at']}`",
        f"- Finished: `{report['finished_at']}`",
        f"- Cases: {summary['passed_cases']} passed, {summary['failed_cases']} failed",
        "",
        "## Correlated scenario runs",
        "",
        "| Case | Batch ID | Events | Status |",
        "| --- | --- | ---: | --- |",
    ]
    for case in report["cases"]:
        lines.append(f"| `{case['name']}` | `{case['batch_id']}` | {case['observed_count']} / {case['expected_count']} | {case['status']} |")
    lines.extend(["", "## Checks", ""])
    for case in report["cases"]:
        lines.append(f"### {case['name']}")
        lines.append("")
        for check in case.get("checks", []):
            lines.append(f"- {check['status']}: `{check['name']}` — {check['detail']}")
        lines.append("")
    if report.get("errors"):
        lines.extend(["## Errors", ""])
        lines.extend(f"- {error}" for error in report["errors"])
        lines.append("")
    return "\n".join(lines)


def write_reports(report: dict[str, Any], report_dir: Path) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "e2e-latest.json"
    markdown_path = report_dir / "e2e-latest.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the local cold-chain pipeline end to end.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=float, default=12.0, help="Seconds to wait for services and each correlated case.")
    parser.add_argument("--startup-delay", type=float, default=1.0, help="Seconds for the listener to subscribe before publishing.")
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    started_at = utc_now()
    run_id = f"e2e-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
    report: dict[str, Any] = {
        "report_version": 1,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": started_at,
        "environment": public_environment(),
        "manifest": str(args.manifest),
        "bridge_url": "",
        "cases": [],
        "errors": [],
        "summary": {"status": "failed", "passed_cases": 0, "failed_cases": 0},
    }
    listener: subprocess.Popen[str] | None = None
    bridge: subprocess.Popen[str] | None = None
    try:
        manifest = load_manifest(args.manifest)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        python = sys.executable
        supports_run_id = generator_supports_run_id(python, env)
        bridge_port = args.bridge_port or free_local_port()
        report["bridge_url"] = f"http://127.0.0.1:{bridge_port}"
        listener = start_process([python, "-m", "backend.temperature_subscriber", "--write-db", "--output-mode", "none"], env=env)
        time.sleep(args.startup_delay)
        if listener.poll() is not None:
            raise RuntimeError(f"temperature subscriber exited with code {listener.returncode}")

        bridge = start_process([python, "-m", "backend.dashboard_bridge", "--host", "127.0.0.1", "--port", str(bridge_port)], env=env)
        base_url = report["bridge_url"]
        wait_for_bridge(base_url, bridge, args.timeout)

        for case in manifest["cases"]:
            batch_id = f"{run_id}-{case['name']}"
            # The application intentionally derives seeded event IDs from the
            # seed. Mix the per-run suffix into the manifest seed so rerunning
            # the verifier cannot collide with an older run while preserving
            # deterministic scenario behavior within this report.
            effective_seed = int(case["seed"]) + int(run_id.rsplit("-", 1)[1], 16)
            command = [python, "-m", "backend.temperature_event_generator", "--sensor", "Pod1", "--vaccine", "pfizer_ultralow", "--scenario", case["scenario"], "--count", str(case["count"]), "--interval-ms", "100", "--seed", str(case["seed"]), "--batch-id", batch_id]
            command[command.index("--seed") + 1] = str(effective_seed)
            if supports_run_id:
                command.extend(["--run-id", run_id])
            command.extend(["--output-mode", "summary"])
            generator = subprocess.run(command, cwd=PROJECT_ROOT, env=env, text=True, capture_output=True, check=False)
            generator_summary: dict[str, Any] | None = None
            for line in reversed(generator.stdout.splitlines()):
                try:
                    candidate = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict) and "published" in candidate:
                    generator_summary = candidate
                    break

            deadline = time.monotonic() + args.timeout
            status_code = 0
            payload: dict[str, Any] = {}
            while time.monotonic() < deadline:
                status_code, payload = read_correlated_events(base_url, batch_id)
                if status_code == 200 and len(payload.get("events", [])) >= int(case["count"]):
                    break
                time.sleep(0.2)
            events = payload.get("events", []) if status_code == 200 else []
            checks = event_checks(case, events, batch_id, run_id)
            checks.append({"name": "generator_command", "status": "passed" if generator.returncode == 0 and generator_summary and generator_summary.get("published") == case["count"] else "failed", "detail": f"returncode={generator.returncode}, summary={generator_summary or 'missing'}"})
            passed = generator.returncode == 0 and status_code == 200 and all(check["status"] == "passed" for check in checks)
            report["cases"].append({
                "name": case["name"],
                "scenario": case["scenario"],
                "batch_id": batch_id,
                "expected_count": case["count"],
                "observed_count": len(events),
                "seed": effective_seed,
                "status": "passed" if passed else "failed",
                "checks": checks,
                "generator": {"command": command, "returncode": generator.returncode, "summary": generator_summary, "stdout": generator.stdout, "stderr": generator.stderr},
                "api_status": status_code,
                "api_scope": payload.get("scope"),
            })
    except Exception as exc:
        report["errors"].append(str(exc))
    finally:
        for process in (bridge, listener):
            if process is None:
                continue
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
            if stdout or stderr:
                report.setdefault("service_logs", []).append({"command": process.args, "returncode": process.returncode, "stdout": stdout, "stderr": stderr})

    report["finished_at"] = utc_now()
    passed_cases = sum(case["status"] == "passed" for case in report["cases"])
    failed_cases = len(report["cases"]) - passed_cases
    report["summary"] = {"status": "passed" if not report["errors"] and failed_cases == 0 and passed_cases == len(report.get("cases", [])) else "failed", "passed_cases": passed_cases, "failed_cases": failed_cases}
    json_path, markdown_path = write_reports(report, args.report_dir)
    print(f"E2E report: {json_path}")
    print(f"E2E report: {markdown_path}")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["summary"]["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
