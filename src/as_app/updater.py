from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UpdateCheck:
    ok: bool
    message: str
    branch: str | None = None
    upstream: str | None = None
    behind: int | None = None
    ahead: int | None = None


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


def check_for_update(repo_root: Path, *, fetch: bool = True) -> UpdateCheck:
    if not _git_ok(repo_root):
        return UpdateCheck(ok=False, message="Repositório não é um git repo.")

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
