"""
ALAS Code Execution Sandbox — Safe, isolated code runner.

Runs Python or Bash code in a subprocess with strict resource limits:
- 30-second timeout
- 256MB memory cap
- Stdout/stderr captured and truncated
- Temp directory per execution, cleaned up after
"""

import os
import json
import shutil
import signal
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("alas.sandbox")


@dataclass
class ExecutionResult:
    """Result of a sandboxed code execution."""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    language: str
    execution_time_ms: float
    truncated: bool = False
    error: Optional[str] = None

    def to_str(self) -> str:
        """Format as a human-readable string for LLM consumption."""
        parts = []
        status = "✅ Success" if self.success else "❌ Failed"
        parts.append(f"{status} ({self.language}, {self.execution_time_ms:.0f}ms, exit code {self.return_code})")

        if self.stdout:
            parts.append(f"\n--- Output ---\n{self.stdout}")
        if self.stderr:
            parts.append(f"\n--- Errors ---\n{self.stderr}")
        if self.error:
            parts.append(f"\n--- Error ---\n{self.error}")
        if self.truncated:
            parts.append("\n⚠️ Output was truncated (exceeded 4KB limit)")

        return "\n".join(parts)

    def to_dict(self) -> dict:
        return asdict(self)


# Maximum output size in characters
MAX_OUTPUT_CHARS = 4096
# Maximum execution time in seconds
MAX_TIMEOUT_SECONDS = 30
# Maximum memory in bytes (256MB)
MAX_MEMORY_BYTES = 256 * 1024 * 1024


def _truncate(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> tuple[str, bool]:
    """Truncate text if it exceeds max_chars."""
    if len(text) > max_chars:
        return text[:max_chars] + "\n...[Output truncated]...", True
    return text, False


def run_python(code: str, working_dir: Optional[str] = None) -> ExecutionResult:
    """
    Execute Python code in a sandboxed subprocess.

    Args:
        code: Python source code to execute.
        working_dir: Optional working directory. If None, uses a temp dir.

    Returns:
        ExecutionResult with stdout, stderr, and metadata.
    """
    import time

    temp_dir = None
    try:
        # Create temporary directory for execution
        if working_dir:
            exec_dir = Path(working_dir)
            exec_dir.mkdir(parents=True, exist_ok=True)
        else:
            temp_dir = tempfile.mkdtemp(prefix="alas_sandbox_")
            exec_dir = Path(temp_dir)

        # Write code to a temp file
        script_path = exec_dir / "_alas_sandbox_script.py"
        script_path.write_text(code, encoding="utf-8")

        # Build the command with resource limits via ulimit
        # We use a wrapper that sets limits before executing
        wrapper_code = f"""
import resource
import sys

# Set memory limit (256MB)
try:
    resource.setrlimit(resource.RLIMIT_AS, ({MAX_MEMORY_BYTES}, {MAX_MEMORY_BYTES}))
except Exception:
    pass

# Set CPU time limit (30s)
try:
    resource.setrlimit(resource.RLIMIT_CPU, ({MAX_TIMEOUT_SECONDS}, {MAX_TIMEOUT_SECONDS}))
except Exception:
    pass

# Execute the user's code
exec(open("{script_path}", encoding="utf-8").read())
"""

        wrapper_path = exec_dir / "_alas_sandbox_wrapper.py"
        wrapper_path.write_text(wrapper_code, encoding="utf-8")

        start_time = time.monotonic()

        result = subprocess.run(
            ["python3", str(wrapper_path)],
            capture_output=True,
            text=True,
            timeout=MAX_TIMEOUT_SECONDS + 5,  # Grace period
            cwd=str(exec_dir),
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",
            },
        )

        elapsed_ms = (time.monotonic() - start_time) * 1000

        stdout, stdout_truncated = _truncate(result.stdout)
        stderr, stderr_truncated = _truncate(result.stderr)

        return ExecutionResult(
            success=result.returncode == 0,
            stdout=stdout,
            stderr=stderr,
            return_code=result.returncode,
            language="python",
            execution_time_ms=elapsed_ms,
            truncated=stdout_truncated or stderr_truncated,
        )

    except subprocess.TimeoutExpired:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr="",
            return_code=-1,
            language="python",
            execution_time_ms=MAX_TIMEOUT_SECONDS * 1000,
            error=f"⏰ Execution timed out after {MAX_TIMEOUT_SECONDS} seconds.",
        )
    except Exception as e:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr="",
            return_code=-1,
            language="python",
            execution_time_ms=0,
            error=f"Sandbox error: {e}",
        )
    finally:
        # Cleanup temp dir
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


def run_bash(code: str, working_dir: Optional[str] = None) -> ExecutionResult:
    """
    Execute Bash script in a sandboxed subprocess.

    Args:
        code: Bash script to execute.
        working_dir: Optional working directory. If None, uses a temp dir.

    Returns:
        ExecutionResult with stdout, stderr, and metadata.
    """
    import time

    temp_dir = None
    try:
        if working_dir:
            exec_dir = Path(working_dir)
            exec_dir.mkdir(parents=True, exist_ok=True)
        else:
            temp_dir = tempfile.mkdtemp(prefix="alas_sandbox_bash_")
            exec_dir = Path(temp_dir)

        # Write script
        script_path = exec_dir / "_alas_sandbox_script.sh"
        script_path.write_text(f"#!/bin/bash\nset -e\n{code}\n", encoding="utf-8")
        script_path.chmod(0o755)

        start_time = time.monotonic()

        # Use ulimit to restrict resources
        wrapped_cmd = (
            f"ulimit -v {MAX_MEMORY_BYTES // 1024} 2>/dev/null; "
            f"ulimit -t {MAX_TIMEOUT_SECONDS} 2>/dev/null; "
            f"bash {script_path}"
        )

        result = subprocess.run(
            ["bash", "-c", wrapped_cmd],
            capture_output=True,
            text=True,
            timeout=MAX_TIMEOUT_SECONDS + 5,
            cwd=str(exec_dir),
        )

        elapsed_ms = (time.monotonic() - start_time) * 1000

        stdout, stdout_truncated = _truncate(result.stdout)
        stderr, stderr_truncated = _truncate(result.stderr)

        return ExecutionResult(
            success=result.returncode == 0,
            stdout=stdout,
            stderr=stderr,
            return_code=result.returncode,
            language="bash",
            execution_time_ms=elapsed_ms,
            truncated=stdout_truncated or stderr_truncated,
        )

    except subprocess.TimeoutExpired:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr="",
            return_code=-1,
            language="bash",
            execution_time_ms=MAX_TIMEOUT_SECONDS * 1000,
            error=f"⏰ Execution timed out after {MAX_TIMEOUT_SECONDS} seconds.",
        )
    except Exception as e:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr="",
            return_code=-1,
            language="bash",
            execution_time_ms=0,
            error=f"Sandbox error: {e}",
        )
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


def run_code(code: str, language: str = "python", working_dir: Optional[str] = None) -> ExecutionResult:
    """
    Execute code in the appropriate sandbox.

    Args:
        code: Source code to execute.
        language: "python" or "bash".
        working_dir: Optional working directory.

    Returns:
        ExecutionResult.
    """
    lang = language.lower().strip()

    if lang in ("python", "python3", "py"):
        logger.info(f"🐍 Sandbox: executing Python code ({len(code)} chars)")
        return run_python(code, working_dir)
    elif lang in ("bash", "sh", "shell"):
        logger.info(f"🐚 Sandbox: executing Bash code ({len(code)} chars)")
        return run_bash(code, working_dir)
    else:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr="",
            return_code=-1,
            language=lang,
            execution_time_ms=0,
            error=f"Unsupported language: {language}. Supported: python, bash.",
        )
