"""
ALAS Git Agent — Git operations as tool functions.

Provides safe, permission-aware git commands that the LLM can invoke.
Each operation runs via subprocess with output capture and safety checks.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger("alas.tools.git")


def _run_git(args: list[str], cwd: str, timeout: int = 15) -> str:
    """Run a git command and return the output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            # Git uses stderr for some normal output (e.g., "Already up to date.")
            if result.returncode != 0:
                output += f"\n--- STDERR ---\n{result.stderr}"
            else:
                output += result.stderr

        if not output.strip():
            output = f"(Command completed with exit code {result.returncode})"

        # Truncate
        if len(output) > 4000:
            output = output[:4000] + "\n...[Output truncated]..."

        return output
    except subprocess.TimeoutExpired:
        return "Error: Git command timed out after 15 seconds."
    except FileNotFoundError:
        return "Error: git is not installed on this system."
    except Exception as e:
        return f"Error running git: {e}"


def _find_repo_root(path: str) -> Optional[str]:
    """Find the git repository root from a given path."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=path,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def git_status(repo_path: str = ".") -> str:
    """
    Show the working tree status of a git repository.
    
    Args:
        repo_path: Path to the repository (or any directory within it).
    
    Returns:
        Git status output.
    """
    root = _find_repo_root(repo_path)
    if not root:
        return f"Error: '{repo_path}' is not inside a git repository."
    return f"📂 Repository: {root}\n\n" + _run_git(["status", "--short", "--branch"], root)


def git_diff(repo_path: str = ".", staged: bool = False) -> str:
    """
    Show the diff of changes in a git repository.
    
    Args:
        repo_path: Path to the repository.
        staged: If True, show staged (cached) diff instead of unstaged.
    
    Returns:
        Git diff output.
    """
    root = _find_repo_root(repo_path)
    if not root:
        return f"Error: '{repo_path}' is not inside a git repository."

    args = ["diff", "--stat"]
    if staged:
        args.append("--cached")

    summary = _run_git(args, root)

    # Also get the full diff but truncated
    detail_args = ["diff"]
    if staged:
        detail_args.append("--cached")
    detail = _run_git(detail_args, root)

    return f"📂 Repository: {root}\n\n{summary}\n\n{detail}"


def git_log(repo_path: str = ".", count: int = 10) -> str:
    """
    Show recent commit history.
    
    Args:
        repo_path: Path to the repository.
        count: Number of commits to show (max 50).
    
    Returns:
        Git log output.
    """
    root = _find_repo_root(repo_path)
    if not root:
        return f"Error: '{repo_path}' is not inside a git repository."

    n = min(max(count, 1), 50)
    return f"📂 Repository: {root}\n\n" + _run_git(
        ["log", f"-{n}", "--oneline", "--graph", "--decorate"],
        root,
    )


def git_branch(repo_path: str = ".", branch_name: str = "", action: str = "list") -> str:
    """
    List, create, or switch git branches.
    
    Args:
        repo_path: Path to the repository.
        branch_name: Name of the branch (required for create/switch).
        action: "list", "create", or "switch".
    
    Returns:
        Git branch output.
    """
    root = _find_repo_root(repo_path)
    if not root:
        return f"Error: '{repo_path}' is not inside a git repository."

    if action == "list":
        return f"📂 Repository: {root}\n\n" + _run_git(["branch", "-a", "-v"], root)
    elif action == "create":
        if not branch_name:
            return "Error: branch_name is required for 'create' action."
        return _run_git(["checkout", "-b", branch_name], root)
    elif action == "switch":
        if not branch_name:
            return "Error: branch_name is required for 'switch' action."
        return _run_git(["checkout", branch_name], root)
    else:
        return f"Unknown action: {action}. Supported: list, create, switch."


def git_commit(repo_path: str = ".", message: str = "", stage_all: bool = True) -> str:
    """
    Stage and commit changes.
    
    Args:
        repo_path: Path to the repository.
        message: Commit message. If empty, auto-generates one.
        stage_all: If True, stages all changes before committing.
    
    Returns:
        Commit result.
    """
    root = _find_repo_root(repo_path)
    if not root:
        return f"Error: '{repo_path}' is not inside a git repository."

    if stage_all:
        stage_result = _run_git(["add", "-A"], root)

    # Check if there's anything to commit
    status = _run_git(["status", "--porcelain"], root)
    if not status.strip() or status.startswith("Error"):
        return "Nothing to commit — working tree is clean."

    if not message:
        # Auto-generate commit message from diff
        diff_stat = _run_git(["diff", "--cached", "--stat"], root)
        message = f"ALAS auto-commit: {diff_stat.split(chr(10))[0].strip()}" if diff_stat.strip() else "ALAS auto-commit"

    result = _run_git(["commit", "-m", message], root)
    return f"🟡 [NOTIFY] Git commit\n\n{result}"


def git_stash(repo_path: str = ".", action: str = "push") -> str:
    """
    Stash or restore changes.
    
    Args:
        repo_path: Path to the repository.
        action: "push" (save changes), "pop" (restore), or "list".
    
    Returns:
        Stash result.
    """
    root = _find_repo_root(repo_path)
    if not root:
        return f"Error: '{repo_path}' is not inside a git repository."

    if action == "push":
        return _run_git(["stash", "push", "-m", "ALAS stash"], root)
    elif action == "pop":
        return _run_git(["stash", "pop"], root)
    elif action == "list":
        return _run_git(["stash", "list"], root)
    else:
        return f"Unknown stash action: {action}. Supported: push, pop, list."


def git_operation(operation: str, repo_path: str = ".", **kwargs) -> str:
    """
    Unified git tool entry point for LLM tool calling.
    
    Args:
        operation: The git operation to perform.
        repo_path: Path to the repository.
        **kwargs: Additional arguments for the specific operation.
    
    Returns:
        Operation result as a string.
    """
    from backend.app.safety.permissions import get_permission_manager, PermissionTier

    op = operation.lower().strip()
    pm = get_permission_manager()

    # Map operations to their functions and permission tiers
    OPERATIONS = {
        "status": (git_status, PermissionTier.AUTO),
        "diff": (git_diff, PermissionTier.AUTO),
        "log": (git_log, PermissionTier.AUTO),
        "branch": (git_branch, PermissionTier.NOTIFY),
        "commit": (git_commit, PermissionTier.NOTIFY),
        "stash": (git_stash, PermissionTier.NOTIFY),
    }

    if op not in OPERATIONS:
        return f"Unknown git operation: {operation}. Supported: {', '.join(OPERATIONS.keys())}"

    func, tier = OPERATIONS[op]

    # For NOTIFY-tier, log the action
    if tier == PermissionTier.NOTIFY:
        logger.info(f"🟡 Git {op} (NOTIFY tier)")

    try:
        result = func(repo_path=repo_path, **kwargs)
        pm.log_action(f"git {op}", tier.value, result[:200])
        return result
    except Exception as e:
        logger.error(f"Git {op} failed: {e}")
        return f"Error performing git {op}: {e}"
