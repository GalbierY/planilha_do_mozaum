from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError


@dataclass(frozen=True)
class GitHubRelease:
    version: str
    tag_name: str
    name: str
    body: str
    html_url: str
    published_at: str
    installer_url: str | None = None


@dataclass(frozen=True)
class UpdateCheckResult:
    has_update: bool
    current_version: str
    latest_version: str
    release: GitHubRelease | None = None
    error: str | None = None


def parse_version(version_str: str) -> tuple[int, ...]:
    """Parse version string like '1.0.0' into tuple of ints."""
    # Remove 'v' prefix if present
    version_str = version_str.lstrip('v')
    # Extract version numbers
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version_str)
    if match:
        return tuple(int(x) for x in match.groups())
    return (0, 0, 0)


def compare_versions(current: str, latest: str) -> int:
    """
    Compare two version strings.
    Returns: -1 if current < latest, 0 if equal, 1 if current > latest
    """
    current_parts = parse_version(current)
    latest_parts = parse_version(latest)
    
    if current_parts < latest_parts:
        return -1
    elif current_parts > latest_parts:
        return 1
    return 0


def get_latest_release(owner: str, repo: str) -> GitHubRelease | None:
    """
    Fetch the latest release from GitHub API.
    
    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
    
    Returns:
        GitHubRelease object if successful, None otherwise
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    
    try:
        req = Request(url)
        req.add_header('Accept', 'application/vnd.github.v3+json')
        req.add_header('User-Agent', 'SAS-Civitas-Updater')
        
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Find installer asset
            installer_url = None
            for asset in data.get('assets', []):
                name = asset.get('name', '').lower()
                if 'instalador' in name or 'installer' in name or name.endswith('.exe'):
                    installer_url = asset.get('browser_download_url')
                    break
            
            return GitHubRelease(
                version=data.get('tag_name', ''),
                tag_name=data.get('tag_name', ''),
                name=data.get('name', ''),
                body=data.get('body', ''),
                html_url=data.get('html_url', ''),
                published_at=data.get('published_at', ''),
                installer_url=installer_url
            )
    except (URLError, json.JSONDecodeError, KeyError) as e:
        print(f"Error fetching GitHub release: {e}")
        return None


def check_for_github_update(
    current_version: str,
    owner: str = "GalbierY",
    repo: str = "planilha_do_mozaum"
) -> UpdateCheckResult:
    """
    Check if there's a new version available on GitHub.
    
    Args:
        current_version: Current application version
        owner: GitHub repository owner
        repo: GitHub repository name
    
    Returns:
        UpdateCheckResult with update information
    """
    release = get_latest_release(owner, repo)
    
    if release is None:
        return UpdateCheckResult(
            has_update=False,
            current_version=current_version,
            latest_version=current_version,
            error="Não foi possível verificar atualizações"
        )
    
    latest_version = release.tag_name.lstrip('v')
    comparison = compare_versions(current_version, latest_version)
    
    return UpdateCheckResult(
        has_update=comparison < 0,
        current_version=current_version,
        latest_version=latest_version,
        release=release
    )


def download_installer(url: str, dest_path: Path) -> bool:
    """
    Download installer from URL.
    
    Args:
        url: URL to download from
        dest_path: Path to save the file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        req = Request(url)
        req.add_header('User-Agent', 'SAS-Civitas-Updater')
        
        with urlopen(req, timeout=60) as response:
            dest_path.write_bytes(response.read())
        return True
    except Exception as e:
        print(f"Error downloading installer: {e}")
        return False