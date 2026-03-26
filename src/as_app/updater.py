from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .github_updater import check_for_github_update, UpdateCheckResult as GitHubUpdateCheckResult


@dataclass(frozen=True)
class UpdateCheck:
    ok: bool
    message: str
    branch: str | None = None
    upstream: str | None = None
    behind: int | None = None
    ahead: int | None = None
    # GitHub update fields
    has_github_update: bool = False
    current_version: str | None = None
    latest_version: str | None = None
    release_name: str | None = None
    release_body: str | None = None
    release_url: str | None = None
    installer_url: str | None = None


def _run_git(repo_root: Path, *args: str, timeout_s: int = 30) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("GCM_INTERACTIVE", "Never")
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        env=env,
        timeout=timeout_s,
        check=False,
    )


def _git_ok(repo_root: Path) -> bool:
    p = _run_git(repo_root, "rev-parse", "--is-inside-work-tree")
    return p.returncode == 0 and (p.stdout or "").strip().lower() == "true"


def _get_branch(repo_root: Path) -> str | None:
    p = _run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    if p.returncode != 0:
        return None
    b = (p.stdout or "").strip()
    return b if b and b != "HEAD" else None


def _get_upstream(repo_root: Path) -> str | None:
    p = _run_git(repo_root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if p.returncode != 0:
        return None
    up = (p.stdout or "").strip()
    return up if up else None


def _is_dirty(repo_root: Path) -> bool:
    p = _run_git(repo_root, "status", "--porcelain")
    return p.returncode == 0 and bool((p.stdout or "").strip())


def check_for_update(repo_root: Path, *, fetch: bool = True, current_version: str = "0.0.0") -> UpdateCheck:
    """
    Check for updates. First tries git-based update, then falls back to GitHub API.
    
    Args:
        repo_root: Root directory of the application
        fetch: Whether to fetch from remote (for git-based updates)
        current_version: Current application version (for GitHub-based updates)
    """
    # Try git-based update first
    if _git_ok(repo_root):
        branch = _get_branch(repo_root)
        upstream = _get_upstream(repo_root)
        if not upstream:
            return UpdateCheck(ok=False, message="Sem upstream configurado (git não sabe de onde puxar).", branch=branch)

        if fetch:
            fetch_p = _run_git(repo_root, "fetch", "--prune", "--tags", timeout_s=60)
            if fetch_p.returncode != 0:
                msg = (fetch_p.stderr or fetch_p.stdout or "").strip() or "Falha no git fetch."
                return UpdateCheck(ok=False, message=msg, branch=branch, upstream=upstream)

        p = _run_git(repo_root, "rev-list", "--left-right", "--count", f"HEAD...{upstream}")
        if p.returncode != 0:
            msg = (p.stderr or p.stdout or "").strip() or "Falha ao comparar versões."
            return UpdateCheck(ok=False, message=msg, branch=branch, upstream=upstream)

        parts = (p.stdout or "").strip().split()
        if len(parts) != 2:
            return UpdateCheck(ok=False, message="Saída inesperada ao comparar versões.", branch=branch, upstream=upstream)

        ahead = int(parts[0])
        behind = int(parts[1])
        return UpdateCheck(
            ok=True,
            message="OK",
            branch=branch,
            upstream=upstream,
            behind=behind,
            ahead=ahead,
        )
    
    # Fallback to GitHub API for non-git installations
    github_result = check_for_github_update(current_version)
    
    if github_result.error:
        return UpdateCheck(ok=False, message=github_result.error)
    
    if not github_result.has_update:
        return UpdateCheck(ok=True, message="Você está usando a versão mais recente.")
    
    release = github_result.release
    return UpdateCheck(
        ok=True,
        message=f"Atualização disponível: {github_result.latest_version}",
        has_github_update=True,
        current_version=github_result.current_version,
        latest_version=github_result.latest_version,
        release_name=release.name if release else None,
        release_body=release.body if release else None,
        release_url=release.html_url if release else None,
        installer_url=release.installer_url if release else None,
    )


def pull_ff_only(repo_root: Path) -> tuple[bool, str]:
    if not _git_ok(repo_root):
        return False, "Repositório não é um git repo."
    if _is_dirty(repo_root):
        return False, "Há alterações locais. Salve/commit/stash antes de atualizar."

    p = _run_git(repo_root, "pull", "--ff-only", timeout_s=120)
    if p.returncode != 0:
        msg = (p.stderr or p.stdout or "").strip() or "Falha no git pull."
        return False, msg
    out = (p.stdout or "").strip()
    return True, (out or "Atualizado com sucesso.")
