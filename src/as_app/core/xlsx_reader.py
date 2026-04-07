from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_REL_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS_REL_OFFICE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def _read_xml(z: zipfile.ZipFile, name: str) -> ET.Element:
    with z.open(name) as f:
        return ET.fromstring(f.read())


def list_sheet_names(xlsx_path: Path) -> list[str]:
    """Retorna a lista de abas disponíveis em um arquivo XLSX."""
    with zipfile.ZipFile(xlsx_path, "r") as z:
        wb = _read_xml(z, "xl/workbook.xml")
        names: list[str] = []
        for sheet in wb.findall(f".//{_q(_NS_MAIN,'sheet')}"):
            name = (sheet.attrib.get("name") or "").strip()
            if name:
                names.append(name)
        return names


def _get_sheet_entry_path(z: zipfile.ZipFile, sheet_name: str) -> str:
    wb = _read_xml(z, "xl/workbook.xml")
    rels = _read_xml(z, "xl/_rels/workbook.xml.rels")

    rel_by_id: dict[str, str] = {}
    for rel in rels.findall(_q(_NS_REL_PKG, "Relationship")):
        rid = rel.attrib.get("Id") or ""
        target = rel.attrib.get("Target") or ""
        rel_by_id[rid] = target

    for sheet in wb.findall(f".//{_q(_NS_MAIN,'sheet')}"):
        name = sheet.attrib.get("name")
        if name != sheet_name:
            continue
        rid = sheet.attrib.get(_q(_NS_REL_OFFICE, "id")) or ""
        target = rel_by_id.get(rid)
        if not target:
            raise ValueError(f"Relationship não encontrado para a aba '{sheet_name}'.")
        target = target.lstrip("/")
        if not target.lower().startswith("xl/"):
            target = f"xl/{target}"
        if target not in z.namelist():
            raise ValueError(f"Arquivo interno '{target}' não encontrado no XLSX.")
        return target

    raise ValueError(f"Aba '{sheet_name}' não encontrada no XLSX.")


def _read_shared_strings(z: zipfile.ZipFile) -> list[str] | None:
    if "xl/sharedStrings.xml" not in z.namelist():
        return None
    root = _read_xml(z, "xl/sharedStrings.xml")
    strings: list[str] = []
    for si in root.findall(_q(_NS_MAIN, "si")):
        parts = [t.text or "" for t in si.findall(f".//{_q(_NS_MAIN,'t')}")]
        strings.append("".join(parts))
    return strings


def read_xlsx_table(xlsx_path: Path, sheet_name: str) -> list[dict[str, Any]]:
    with zipfile.ZipFile(xlsx_path, "r") as z:
        shared = _read_shared_strings(z)
        sheet_path = _get_sheet_entry_path(z, sheet_name)
        root = _read_xml(z, sheet_path)

        sheet_data = root.find(_q(_NS_MAIN, "sheetData"))
        if sheet_data is None:
            return []

        rows = list(sheet_data.findall(_q(_NS_MAIN, "row")))
        if not rows:
            return []

        def cell_value(cell: ET.Element) -> str:
            t = cell.attrib.get("t")
            if t == "inlineStr":
                parts = [n.text or "" for n in cell.findall(f".//{_q(_NS_MAIN,'t')}")]
                return "".join(parts)
            v = cell.find(_q(_NS_MAIN, "v"))
            if v is None or v.text is None:
                return ""
            raw = v.text
            if t == "s" and shared is not None:
                try:
                    return shared[int(raw)]
                except (ValueError, IndexError):
                    return ""
            return raw

        header_row = rows[0]
        headers: dict[str, str] = {}
        for cell in header_row.findall(_q(_NS_MAIN, "c")):
            ref = cell.attrib.get("r") or ""
            col = re.match(r"^[A-Z]+", ref)
            if not col:
                continue
            headers[col.group(0)] = cell_value(cell).strip()

        records: list[dict[str, Any]] = []
        for row in rows[1:]:
            row_num = int(row.attrib.get("r") or "0")
            rec: dict[str, Any] = {"__row": row_num}
            any_value = False

            for cell in row.findall(_q(_NS_MAIN, "c")):
                ref = cell.attrib.get("r") or ""
                col_match = re.match(r"^[A-Z]+", ref)
                if not col_match:
                    continue
                col = col_match.group(0)
                header = headers.get(col, "").strip()
                if not header:
                    continue
                value = cell_value(cell)
                if value.strip():
                    any_value = True
                rec[header] = value

            if any_value:
                records.append(rec)

        return records


def read_criancas_column(xlsx_path: Path, sheet_name: str) -> list[str]:
    """Lê apenas a coluna 'Crianças' do Excel para o workflow."""
    with zipfile.ZipFile(xlsx_path, "r") as z:
        shared = _read_shared_strings(z)
        sheet_path = _get_sheet_entry_path(z, sheet_name)
        root = _read_xml(z, sheet_path)

        sheet_data = root.find(_q(_NS_MAIN, "sheetData"))
        if sheet_data is None:
            return []

        rows = list(sheet_data.findall(_q(_NS_MAIN, "row")))
        if not rows:
            return []

        def cell_value(cell: ET.Element) -> str:
            t = cell.attrib.get("t")
            if t == "inlineStr":
                parts = [n.text or "" for n in cell.findall(f".//{_q(_NS_MAIN,'t')}")]
                return "".join(parts)
            v = cell.find(_q(_NS_MAIN, "v"))
            if v is None or v.text is None:
                return ""
            raw = v.text
            if t == "s" and shared is not None:
                try:
                    return shared[int(raw)]
                except (ValueError, IndexError):
                    return ""
            return raw

        # Encontrar a coluna "Crianças"
        header_row = rows[0]
        crianca_col = None
        for cell in header_row.findall(_q(_NS_MAIN, "c")):
            ref = cell.attrib.get("r") or ""
            col = re.match(r"^[A-Z]+", ref)
            if not col:
                continue
            header = cell_value(cell).strip()
            if header.lower() == "crianças":
                crianca_col = col.group(0)
                break

        if not crianca_col:
            return []

        nomes = []
        for row in rows[1:]:
            for cell in row.findall(_q(_NS_MAIN, "c")):
                ref = cell.attrib.get("r") or ""
                col_match = re.match(r"^[A-Z]+", ref)
                if not col_match:
                    continue
                col = col_match.group(0)
                if col == crianca_col:
                    value = cell_value(cell).strip()
                    if value:
                        nomes.append(value)
                    break

        return nomes
