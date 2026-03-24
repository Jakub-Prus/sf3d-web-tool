from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from app.core.config import Settings

RUNNER_IMPORT_CHECK_TIMEOUT_SECONDS = 10
RUNNER_FAILURE_SUMMARY_MAX_LINES = 3
RUNNER_FAILURE_SUMMARY_MAX_LENGTH = 240
RUNNER_IMPORT_CHECK_SNIPPET = "import run"


@dataclass(frozen=True)
class RunnerImportProbeResult:
    is_ready: bool
    warning: str | None = None


def summarize_runner_failure(stdout_text: str, stderr_text: str) -> str | None:
    for candidate in (stderr_text, stdout_text):
        lines = [line.strip() for line in candidate.splitlines() if line.strip()]
        if not lines:
            continue

        summary = " | ".join(lines[-RUNNER_FAILURE_SUMMARY_MAX_LINES:])
        if len(summary) > RUNNER_FAILURE_SUMMARY_MAX_LENGTH:
            return f"{summary[:RUNNER_FAILURE_SUMMARY_MAX_LENGTH - 3]}..."
        return summary

    return None


def probe_runner_import(settings: Settings) -> RunnerImportProbeResult:
    if not settings.is_sf3d_repo_ready() or not settings.is_sf3d_python_ready():
        return RunnerImportProbeResult(is_ready=False)

    probe_env = os.environ.copy()
    probe_env["PYTHONDONTWRITEBYTECODE"] = "1"

    try:
        completed_process = subprocess.run(
            [settings.sf3d_python_executable, "-c", RUNNER_IMPORT_CHECK_SNIPPET],
            cwd=str(settings.sf3d_repo_dir),
            env=probe_env,
            capture_output=True,
            text=True,
            timeout=RUNNER_IMPORT_CHECK_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return RunnerImportProbeResult(
            is_ready=False,
            warning=(
                "The configured SF3D runner import check timed out after "
                f"{RUNNER_IMPORT_CHECK_TIMEOUT_SECONDS} seconds."
            ),
        )
    except (OSError, ValueError, NotImplementedError):
        return RunnerImportProbeResult(
            is_ready=False,
            warning=(
                "The configured SF3D runner import check could not be started. "
                "Check the Python path and upstream environment setup."
            ),
        )

    if completed_process.returncode == 0:
        return RunnerImportProbeResult(is_ready=True)

    summary = summarize_runner_failure(completed_process.stdout, completed_process.stderr)
    warning = "The configured SF3D runner environment failed an import preflight check."
    if summary:
        warning = f"{warning} {summary}"

    return RunnerImportProbeResult(is_ready=False, warning=warning)
