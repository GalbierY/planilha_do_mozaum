from __future__ import annotations

from .cadastros_tab import build_cadastros_tab
from .stats_tab import build_stats_tab
from .reports_tab import build_reports_tab
from .backup_tab import build_backup_tab
from .users_tab import build_users_tab
from .audit_tab import build_audit_tab
from .workflow_tab import build_workflow_tab
from .history_tab import build_history_tab

__all__ = [
    "build_cadastros_tab",
    "build_stats_tab",
    "build_reports_tab",
    "build_backup_tab",
    "build_users_tab",
    "build_audit_tab",
    "build_workflow_tab",
    "build_history_tab",
]
