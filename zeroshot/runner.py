"""Zeroshot graph runner and verification harness for ai-engineering-team."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ZeroshotMetrics:
    duration_seconds: float = 0.0
    iterations: int = 0
    verdict: str = "unknown"
    syntax_error_detected: bool = False
    syntax_error_repaired: bool = False
    raw_events_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ZeroshotRunResult:
    success: bool
    exit_code: int
    metrics: ZeroshotMetrics = field(default_factory=ZeroshotMetrics)
    stdout: str = ""
    stderr: str = ""
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "metrics": self.metrics.to_dict(),
            "stdout": self.stdout,
            "stderr": self.stderr,
            "reasons": self.reasons,
        }


def resolve_zeroshot_bin() -> str:
    """Locate the native Zeroshot binary or wrapper."""
    # 1. Explicit env var
    env_bin = os.environ.get("ZEROSHOT_BIN")
    if env_bin and os.path.isfile(env_bin) and os.access(env_bin, os.X_OK):
        return env_bin

    # 2. Local trial repo bin wrapper
    local_bin = Path(__file__).resolve().parent / "bin" / "zeroshot"
    if local_bin.is_file() and os.access(local_bin, os.X_OK):
        return str(local_bin)

    # 3. Known npm cache native path
    npm_native = Path("/home/tomaasz/.cache/npm/_npx/f4959877fc7f2822/node_modules/@the-open-engine-company/zeroshot/bin/native/zeroshot")
    if npm_native.is_file() and os.access(npm_native, os.X_OK):
        return str(npm_native)

    # 4. Global PATH
    which_bin = shutil.which("zeroshot")
    if which_bin:
        return which_bin

    raise FileNotFoundError("Zeroshot executable could not be resolved.")


def validate_zeroshot_graph(
    graph_path: Path | str,
    runtime_path: Path | str,
    input_path: Path | str,
) -> bool:
    """Validate graph, runtime-config and input JSON definitions using Zeroshot engine."""
    bin_path = resolve_zeroshot_bin()
    cmd = [
        bin_path,
        "run",
        "--title",
        "Validation",
        "--graph",
        str(graph_path),
        "--runtime-config",
        str(runtime_path),
        "--input",
        str(input_path),
        "--validate-only",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return False
    try:
        data = json.loads(proc.stdout.strip())
        return bool(data.get("valid", False))
    except json.JSONDecodeError:
        return False


def run_zeroshot_verification(
    graph_path: Path | str,
    runtime_path: Path | str,
    input_path: Path | str,
    timeout_seconds: int = 180,
    target_cwd: Optional[Path | str] = None,
) -> ZeroshotRunResult:
    """Execute Zeroshot verification graph with timing and metric tracking."""
    bin_path = resolve_zeroshot_bin()
    cmd = [
        bin_path,
        "run",
        "--title",
        "Trial Verification Loop",
        "--graph",
        str(graph_path),
        "--runtime-config",
        str(runtime_path),
        "--input",
        str(input_path),
    ]
    start_time = time.monotonic()
    cwd = str(target_cwd) if target_cwd else None

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        duration = time.monotonic() - start_time
        metrics = ZeroshotMetrics(duration_seconds=round(duration, 2))

        success = proc.returncode == 0
        reasons: List[str] = []
        if not success:
            reasons.append(f"Zeroshot process exited with code {proc.returncode}")

        return ZeroshotRunResult(
            success=success,
            exit_code=proc.returncode,
            metrics=metrics,
            stdout=proc.stdout,
            stderr=proc.stderr,
            reasons=reasons,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start_time
        metrics = ZeroshotMetrics(duration_seconds=round(duration, 2))
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "Timeout expired")
        return ZeroshotRunResult(
            success=False,
            exit_code=124,
            metrics=metrics,
            stdout=out,
            stderr=err,
            reasons=[f"Circuit breaker: execution exceeded timeout of {timeout_seconds}s"],
        )
