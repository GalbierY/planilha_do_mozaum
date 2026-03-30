from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .util import now_iso, stable_key, write_json_atomic


DEFAULT_TAGS = ["Violencia", "TEA"]


def _normalize_tags(raw_tags: Any) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    if isinstance(raw_tags, str):
        source = [raw_tags]
    elif isinstance(raw_tags, list):
        source = raw_tags
    elif raw_tags is None:
        source = []
    else:
        source = [str(raw_tags)]
    for raw in source:
        t = ("" if raw is None else str(raw)).strip()
        if not t:
            continue
        k = t.casefold()
        if k in seen:
            continue
        seen.add(k)
        items.append(t)
    return items


def _ensure_catalog_defaults(raw_catalog: Any) -> list[str]:
    tags = _normalize_tags(raw_catalog)
    by_key = {t.casefold(): t for t in tags}
    for default_tag in DEFAULT_TAGS:
        k = default_tag.casefold()
        if k not in by_key:
            tags.append(default_tag)
            by_key[k] = default_tag
    tags.sort(key=str.casefold)
    return tags


@dataclass
class ImportResult:
    batch_id: str
    inserted: int
    updated: int
    skipped: int
    total: int


class JsonStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _empty_db(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "generated_at": now_iso(),
            "children": [],
            "attendances": [],
            "import_batches": [],
            "audit_log": [],
            "attachments": [],
            "users": [],
            "tags_catalog": list(DEFAULT_TAGS),
        }

    def _audit(
        self,
        db: dict[str, Any],
        *,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str | None,
        details: dict[str, Any],
    ) -> None:
        entry = {
            "id": str(uuid.uuid4()),
            "at": now_iso(),
            "actor": actor,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details,
        }
        (db.setdefault("audit_log", [])).append(entry)

    def log_event(self, *, actor: str, action: str, details: dict[str, Any]) -> None:
        db = self.load()
        self._audit(
            db,
            actor=actor,
            action=action,
            entity_type="system",
            entity_id=None,
            details=details,
        )
        self.save(db)

    @staticmethod
    def _diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        keys = set(before.keys()) | set(after.keys())
        changed: dict[str, Any] = {}
        for k in sorted(keys):
            if k in {"updated_at"}:
                continue
            if before.get(k) != after.get(k):
                changed[k] = {"from": before.get(k), "to": after.get(k)}
        return changed

    def _ensure_v2(self, db: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        changed = False
        version = int(db.get("schema_version") or 1)

        if version < 2:
            alunos = list(db.get("alunos") or [])
            children: list[dict[str, Any]] = []
            attendances: list[dict[str, Any]] = []

            for a in alunos:
                child = dict(a)
                atendimento_text = (child.pop("atendimento_realizado", "") or "").strip()
                vd_text = (child.pop("vd", "") or "").strip()

                # Child fields
                child.setdefault("created_at", now_iso())
                child.setdefault("updated_at", child.get("created_at"))
                child.setdefault("source", {"type": "imported"})
                children.append(child)

                # Initial imported attendance (only if there is content)
                if atendimento_text or vd_text:
                    occurred_at = (
                        child.get("imported_at")
                        or child.get("updated_at")
                        or child.get("created_at")
                        or now_iso()
                    )
                    ext = stable_key(
                        f"migrate_v1|{child.get('external_key','')}|{occurred_at}"
                    )
                    attendances.append(
                        {
                            "id": str(uuid.uuid4()),
                            "external_key": ext,
                            "child_id": child.get("id"),
                            "occurred_at": occurred_at,
                            "tipo": "importado",
                            "profissional": "",
                            "registrado_por": "migrate",
                            "resultado": "",
                            "atendimento_text": atendimento_text,
                            "vd_text": vd_text,
                            "created_at": now_iso(),
                            "updated_at": now_iso(),
                            "source": child.get("source") or {"type": "migrate"},
                        }
                    )

            db.pop("alunos", None)
            db["schema_version"] = 2
            db["children"] = children
            db["attendances"] = attendances
            db.setdefault("import_batches", [])
            db.setdefault("audit_log", [])
            db.setdefault("attachments", [])
            db.setdefault("users", [])
            db.setdefault("tags_catalog", list(DEFAULT_TAGS))
            changed = True
            version = 2

        # Ensure required keys
        for k, default in {
            "children": [],
            "attendances": [],
            "import_batches": [],
            "audit_log": [],
            "attachments": [],
            "users": [],
            "tags_catalog": list(DEFAULT_TAGS),
        }.items():
            if k not in db or db.get(k) is None:
                db[k] = default
                changed = True

        catalog = _ensure_catalog_defaults(db.get("tags_catalog"))
        if db.get("tags_catalog") != catalog:
            db["tags_catalog"] = list(catalog)
            changed = True

        catalog_keys = {t.casefold() for t in catalog}
        for child in db.get("children") or []:
            normalized = _normalize_tags(child.get("tags"))
            if child.get("tags") != normalized:
                child["tags"] = normalized
                changed = True
            for tag in normalized:
                key = tag.casefold()
                if key in catalog_keys:
                    continue
                catalog.append(tag)
                catalog_keys.add(key)
                changed = True
        if db.get("tags_catalog") != catalog:
            db["tags_catalog"] = list(catalog)
            changed = True

        if db.get("schema_version") != 2:
            db["schema_version"] = 2
            changed = True

        return db, changed

    def load(self) -> dict[str, Any]:
        if not self.db_path.exists():
            db = self._empty_db()
            write_json_atomic(self.db_path, db)
            return db
        text = self.db_path.read_text(encoding="utf-8")
        if not text.strip():
            db = self._empty_db()
            write_json_atomic(self.db_path, db)
            return db
        db = json.loads(text)
        db, changed = self._ensure_v2(db)
        if changed:
            self.save(db)
        return db

    def save(self, db: dict[str, Any]) -> None:
        db["generated_at"] = now_iso()
        write_json_atomic(self.db_path, db)

    def list_children(self) -> list[dict[str, Any]]:
        db = self.load()
        children = list(db.get("children") or [])
        children.sort(key=lambda a: (a.get("nome") or "").lower())
        return children

    def list_attendances(self, child_id: str) -> list[dict[str, Any]]:
        db = self.load()
        atts = [a for a in (db.get("attendances") or []) if a.get("child_id") == child_id]
        atts.sort(key=lambda a: (a.get("occurred_at") or ""), reverse=True)
        return atts

    def list_attachments(self, attendance_id: str) -> list[dict[str, Any]]:
        db = self.load()
        items = [a for a in (db.get("attachments") or []) if a.get("attendance_id") == attendance_id]
        items.sort(key=lambda a: (a.get("added_at") or ""), reverse=True)
        return items

    def add_attachment(self, attachment: dict[str, Any], *, actor: str | None = None) -> dict[str, Any]:
        db = self.load()
        items: list[dict[str, Any]] = list(db.get("attachments") or [])
        created = now_iso()
        attachment = {**attachment}
        attachment.setdefault("id", str(uuid.uuid4()))
        attachment.setdefault("added_at", created)
        items.append(attachment)
        db["attachments"] = items
        if actor:
            self._audit(
                db,
                actor=actor,
                action="attachment.add",
                entity_type="attachment",
                entity_id=attachment.get("id"),
                details={"attachment": attachment},
            )
        self.save(db)
        return attachment

    def remove_attachment(self, attachment_id: str, *, actor: str | None = None) -> bool:
        db = self.load()
        items: list[dict[str, Any]] = list(db.get("attachments") or [])
        before = len(items)
        items = [a for a in items if a.get("id") != attachment_id]
        if len(items) == before:
            return False
        db["attachments"] = items
        if actor:
            self._audit(
                db,
                actor=actor,
                action="attachment.remove",
                entity_type="attachment",
                entity_id=attachment_id,
                details={},
            )
        self.save(db)
        return True

    def list_users(self) -> list[dict[str, Any]]:
        db = self.load()
        users = list(db.get("users") or [])
        users.sort(key=lambda u: (u.get("username") or "").lower())
        return users

    def list_tags(self) -> list[str]:
        db = self.load()
        tags = _ensure_catalog_defaults(db.get("tags_catalog"))
        if db.get("tags_catalog") != tags:
            db["tags_catalog"] = list(tags)
            self.save(db)
        return list(tags)

    def add_tag(self, tag_name: str, *, actor: str | None = None) -> tuple[bool, str]:
        candidate = (tag_name or "").strip()
        if not candidate:
            return False, ""

        db = self.load()
        tags = _ensure_catalog_defaults(db.get("tags_catalog"))
        by_key = {t.casefold(): t for t in tags}
        key = candidate.casefold()
        if key in by_key:
            return False, by_key[key]

        tags.append(candidate)
        tags = _ensure_catalog_defaults(tags)
        db["tags_catalog"] = tags
        if actor:
            self._audit(
                db,
                actor=actor,
                action="tag.add",
                entity_type="tag",
                entity_id=key,
                details={"name": candidate},
            )
        self.save(db)
        return True, candidate

    def upsert_user(self, user: dict[str, Any], *, actor: str | None = None) -> tuple[str, dict[str, Any]]:
        db = self.load()
        users: list[dict[str, Any]] = list(db.get("users") or [])

        existing = None
        user_id = (user.get("id") or "").strip()
        username = (user.get("username") or "").strip().lower()
        if user_id:
            existing = next((u for u in users if u.get("id") == user_id), None)
        if existing is None and username:
            existing = next((u for u in users if (u.get("username") or "").strip().lower() == username), None)

        if existing is None:
            new_id = str(uuid.uuid4())
            created = now_iso()
            user = {**user}
            user["id"] = new_id
            user["created_at"] = created
            user["updated_at"] = created
            users.append(user)
            db["users"] = users
            if actor:
                self._audit(
                    db,
                    actor=actor,
                    action="user.insert",
                    entity_type="user",
                    entity_id=new_id,
                    details={"user": {"id": new_id, "username": user.get("username"), "role": user.get("role")}},
                )
            self.save(db)
            return "inserted", user

        before = dict(existing)
        for k, v in user.items():
            if k in {"id", "created_at"}:
                continue
            existing[k] = v
        existing["updated_at"] = now_iso()
        db["users"] = users
        if actor:
            self._audit(
                db,
                actor=actor,
                action="user.update",
                entity_type="user",
                entity_id=existing.get("id"),
                details={"diff": self._diff(before, existing)},
            )
        self.save(db)
        return "updated", existing

    def merge_children(self, *, keep_id: str, merge_id: str, actor: str) -> bool:
        if keep_id == merge_id:
            return False
        db = self.load()
        children: list[dict[str, Any]] = list(db.get("children") or [])
        keep = next((c for c in children if c.get("id") == keep_id), None)
        merge = next((c for c in children if c.get("id") == merge_id), None)
        if not keep or not merge:
            return False

        # Merge tags from both children.
        merged_tags = _normalize_tags((keep.get("tags") or []) + (merge.get("tags") or []))
        keep["tags"] = merged_tags

        # Move attendances
        moved = 0
        for att in db.get("attendances") or []:
            if att.get("child_id") == merge_id:
                att["child_id"] = keep_id
                moved += 1

        children = [c for c in children if c.get("id") != merge_id]
        db["children"] = children

        self._audit(
            db,
            actor=actor,
            action="child.merge",
            entity_type="child",
            entity_id=keep_id,
            details={
                "keep_id": keep_id,
                "merge_id": merge_id,
                "moved_attendances": moved,
                "merged_child": {"id": merge.get("id"), "nome": merge.get("nome"), "escola": merge.get("escola")},
                "tags": merged_tags,
            },
        )
        self.save(db)
        return True

    def upsert_child(self, child: dict[str, Any], *, actor: str | None = None) -> tuple[str, dict[str, Any]]:
        db = self.load()
        children: list[dict[str, Any]] = list(db.get("children") or [])
        tags_catalog = _ensure_catalog_defaults(db.get("tags_catalog"))
        tags_catalog_keys = {t.casefold() for t in tags_catalog}

        child = {**child}
        if "tags" in child:
            child["tags"] = _normalize_tags(child.get("tags"))
        else:
            child.setdefault("tags", [])

        existing = None
        child_id = (child.get("id") or "").strip()
        if child_id:
            existing = next((a for a in children if a.get("id") == child_id), None)
        if existing is None:
            ext = (child.get("external_key") or "").strip()
            if ext:
                existing = next((a for a in children if a.get("external_key") == ext), None)

        if existing is None:
            new_id = str(uuid.uuid4())
            created = now_iso()
            child = {**child}
            child["id"] = new_id
            child["created_at"] = created
            child["updated_at"] = created
            child.setdefault("source", {"type": "manual"})
            children.append(child)
            db["children"] = children
            for tag in _normalize_tags(child.get("tags")):
                key = tag.casefold()
                if key in tags_catalog_keys:
                    continue
                tags_catalog.append(tag)
                tags_catalog_keys.add(key)
            db["tags_catalog"] = _ensure_catalog_defaults(tags_catalog)
            if actor:
                self._audit(
                    db,
                    actor=actor,
                    action="child.insert",
                    entity_type="child",
                    entity_id=new_id,
                    details={"child": child},
                )
            self.save(db)
            return "inserted", child

        skip = {"id", "created_at"}

        before = dict(existing)
        for k, v in child.items():
            if k in skip:
                continue
            existing[k] = v
        existing["updated_at"] = now_iso()
        existing["tags"] = _normalize_tags(existing.get("tags"))
        for tag in existing["tags"]:
            key = tag.casefold()
            if key in tags_catalog_keys:
                continue
            tags_catalog.append(tag)
            tags_catalog_keys.add(key)

        db["children"] = children
        db["tags_catalog"] = _ensure_catalog_defaults(tags_catalog)
        if actor:
            self._audit(
                db,
                actor=actor,
                action="child.update",
                entity_type="child",
                entity_id=existing.get("id"),
                details={"diff": self._diff(before, existing)},
            )
        self.save(db)
        return "updated", existing

    def add_attendance(self, attendance: dict[str, Any], *, actor: str | None = None) -> dict[str, Any]:
        db = self.load()
        attendances: list[dict[str, Any]] = list(db.get("attendances") or [])

        created = now_iso()
        attendance = {**attendance}
        attendance.setdefault("id", str(uuid.uuid4()))
        attendance.setdefault("created_at", created)
        attendance.setdefault("updated_at", created)
        if actor:
            attendance.setdefault("registrado_por", actor)
        attendances.append(attendance)
        db["attendances"] = attendances
        if actor:
            self._audit(
                db,
                actor=actor,
                action="attendance.add",
                entity_type="attendance",
                entity_id=attendance.get("id"),
                details={"attendance": attendance},
            )
        self.save(db)
        return attendance

    def update_attendance(
        self,
        attendance_id: str,
        patch: dict[str, Any],
        *,
        actor: str | None = None,
    ) -> dict[str, Any] | None:
        db = self.load()
        attendances: list[dict[str, Any]] = list(db.get("attendances") or [])

        target = next((a for a in attendances if (a.get("id") or "") == attendance_id), None)
        if target is None:
            return None

        before = dict(target)
        skip = {"id", "child_id", "created_at"}
        for k, v in (patch or {}).items():
            if k in skip:
                continue
            target[k] = v
        target["updated_at"] = now_iso()

        db["attendances"] = attendances
        if actor:
            self._audit(
                db,
                actor=actor,
                action="attendance.update",
                entity_type="attendance",
                entity_id=attendance_id,
                details={"diff": self._diff(before, target)},
            )
        self.save(db)
        return target

    def new_child_from_form(
        self,
        *,
        child_id: str | None,
        nome: str,
        idade: str,
        escola: str,
        data_nascimento_iso: str | None,
        contato: str | None,
        endereco: str | None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        age = None
        idade = (idade or "").strip()
        if idade:
            try:
                age = int(idade)
            except ValueError:
                age = None

        nome = (nome or "").strip()
        escola = (escola or "").strip()
        birth = (data_nascimento_iso or "").strip()
        contato = (contato or "").strip()
        endereco = (endereco or "").strip()
        seed = f"{nome}|{birth}|{escola}".lower()
        ext = stable_key(seed) if seed.replace("|", "").strip() else None

        return {
            "id": (child_id or "").strip() or None,
            "external_key": ext,
            "nome": nome,
            "idade": age,
            "escola": escola,
            "data_nascimento": birth or None,
            "contato": contato or None,
            "endereco": endereco or None,
            "tags": _normalize_tags(tags),
            "workflow_status": False,
            "source": {"type": "manual"},
        }

def build_external_key(nome: str, birth_iso: str | None, escola: str) -> str:
    seed = f"{(nome or '').strip()}|{(birth_iso or '').strip()}|{(escola or '').strip()}".lower()
    return stable_key(seed)
