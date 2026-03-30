from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class UserRole(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

    @classmethod
    def from_str(cls, value: str | None) -> "UserRole":
        raw = (value or "").strip().lower()
        if raw == cls.ADMIN.value:
            return cls.ADMIN
        if raw == cls.EDITOR.value:
            return cls.EDITOR
        return cls.VIEWER


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"

    @classmethod
    def from_bool(cls, value: bool | None) -> "WorkflowStatus":
        return cls.COMPLETED if bool(value) else cls.PENDING


class ReportKind(str, Enum):
    PENDING = "pending"
    FALTAS = "faltas"
    BY_SCHOOL = "by_school"
    ATT_BY_MONTH = "att_by_month"
    ATT_DETAIL = "att_detail"

    @classmethod
    def from_label(cls, label: str) -> "ReportKind":
        normalized = (label or "").strip()
        mapping = {
            "Pendencias de atendimento": cls.PENDING,
            "Faltas registradas": cls.FALTAS,
            "Resumo por escola": cls.BY_SCHOOL,
            "Atendimentos por mes": cls.ATT_BY_MONTH,
            "Detalhamento de atendimentos": cls.ATT_DETAIL,
        }
        return mapping.get(normalized, cls.PENDING)


@dataclass
class Child:
    id: str | None
    nome: str
    idade: int | None
    escola: str
    data_nascimento: str | None
    contato: str | None
    endereco: str | None
    tags: list[str]
    workflow_status: bool
    source: dict[str, Any] | None
    created_at: str | None
    updated_at: str | None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Child":
        return cls(
            id=raw.get("id"),
            nome=str(raw.get("nome") or "").strip(),
            idade=raw.get("idade"),
            escola=str(raw.get("escola") or "").strip(),
            data_nascimento=raw.get("data_nascimento"),
            contato=raw.get("contato"),
            endereco=raw.get("endereco"),
            tags=[str(t).strip() for t in (raw.get("tags") or []) if str(t).strip()],
            workflow_status=bool(raw.get("workflow_status", False)),
            source=raw.get("source"),
            created_at=raw.get("created_at"),
            updated_at=raw.get("updated_at"),
        )


@dataclass
class Attendance:
    id: str | None
    child_id: str
    occurred_at: str | None
    tipo: str
    profissional: str
    resultado: str
    atendimento_text: str
    vd_text: str
    registrado_por: str | None
    created_at: str | None
    updated_at: str | None
    source: dict[str, Any] | None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Attendance":
        return cls(
            id=raw.get("id"),
            child_id=str(raw.get("child_id") or "").strip(),
            occurred_at=raw.get("occurred_at"),
            tipo=str(raw.get("tipo") or "").strip(),
            profissional=str(raw.get("profissional") or "").strip(),
            resultado=str(raw.get("resultado") or "").strip(),
            atendimento_text=str(raw.get("atendimento_text") or "").strip(),
            vd_text=str(raw.get("vd_text") or "").strip(),
            registrado_por=raw.get("registrado_por"),
            created_at=raw.get("created_at"),
            updated_at=raw.get("updated_at"),
            source=raw.get("source"),
        )


@dataclass
class User:
    id: str | None
    username: str
    role: UserRole
    active: bool
    salt_hex: str | None
    hash_hex: str | None
    created_at: str | None
    updated_at: str | None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "User":
        return cls(
            id=raw.get("id"),
            username=str(raw.get("username") or "").strip(),
            role=UserRole.from_str(str(raw.get("role") or "")),
            active=bool(raw.get("active", True)),
            salt_hex=raw.get("salt_hex"),
            hash_hex=raw.get("hash_hex"),
            created_at=raw.get("created_at"),
            updated_at=raw.get("updated_at"),
        )
