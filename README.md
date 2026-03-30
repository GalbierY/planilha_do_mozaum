# SAS Civitas

Desktop app (Tkinter) for social assistance workflows: child records, sessions, attachments, reports, and local data management without a server.

## Main features

- Child records with fast edit form.
- Multi-tag support per child (for example: `Violencia`, `TEA`) with user-defined tags.
- Session history (including home visits) with create/edit flow.
- Attachment support per session.
- Reports and exports.
- Basic statistics dashboard.
- Tag-based filtering and tag distribution stats.
- Backup and restore.
- Access control (`admin`, `editor`, `viewer`) and audit trail.
- XLSX import workflow with pending/completed status.
- Auto-update via `git pull` (dev clone) or GitHub Releases (installed build).
- UI language support:
  - Default: `pt-BR`
  - Optional: `en`

## Requirements

- Windows 10/11
- Python 3 (`py` launcher available)
- Internet access to install dependencies
- Optional for installer packaging: Inno Setup (`iscc.exe`)

## Run (development)

1. Clone this repository.
2. From project root, run:

```cmd
py -3 bootstrap.py
```

Or use:

```cmd
start_gui.cmd
```

`bootstrap.py` creates `.venv`, installs `requirements.txt`, and starts the GUI.

## First access

- If there is no local user yet, the app opens an admin setup dialog.
- After that, login is required.

## Quick usage flow

1. In `Cadastros` (Records), search and select a child.
2. Use action buttons to create/update records.
3. In `Historico` (History), create/edit sessions.
4. In `Workflow`, import and track pending/completed items.
5. Use `Relatorios`, `Estatisticas`, and `Backup` as needed.

## Keyboard shortcuts

- `Ctrl+F`: focus search
- `Ctrl+N`: new record form
- `Ctrl+S`: save record
- `Ctrl+Enter`: new session
- `Ctrl+E`: edit selected session
- `Ctrl+I`: import records
- `Alt+1..7`: switch main tabs
- `Alt+8`: `Usuarios` tab (admin-only, when available)

## UI language

- Default language is `pt-BR`.
- End users can switch language in-app using the `Idioma / Language` button.
- Current supported languages:
  - `pt-BR`
  - `en`

Config key:

```json
{
  "ui_language": "pt-BR"
}
```

## Data location

In development mode, data lives in this project folder.

In packaged installations (`.exe` / installer), data is stored in:

```text
%LOCALAPPDATA%\SAS Civitas\UserData\
```

Main files/folders:

- `config\config.json`
- `data\metadata\as_db.json`
- `data\attachments\`
- `data\backups\`
- `data\exports\`
- `data\AssistenteSocial.xlsx`

You can override data root with:

```text
SAS_DATA_DIR
```

## Configuration

Main config file:

```text
config/config.json
```

Common keys:

- `app_name`
- `app_version`
- `xlsx_default_path`
- `xlsx_default_sheet`
- `auto_update_enabled`
- `update_check_minutes`
- `ui_language`

## Build and distribution

Build executable (PyInstaller):

```cmd
packaging\build_exe.cmd
```

Output:

```text
artifacts\pyinstaller-dist\SAS Civitas\SAS Civitas.exe
```

Build installer (Inno Setup):

```cmd
packaging\build_installer.cmd
```

Output:

```text
artifacts\inno-output\SAS Civitas - Instalador.exe
```

Sync version from `config.json` into installer script:

```cmd
packaging\sync_version.cmd
```

Prepare release artifacts (`portable`, installer, `SHA256SUMS.txt`):

```cmd
packaging\preparar_release.cmd
```

Output:

```text
release\
```

## Auto-update behavior

- Git clone: checks updates and applies `git pull --ff-only`.
- Non-git installation: checks GitHub Releases, downloads installer, and opens it for manual update.

## Project structure

- `src/as_app/`: application source code
- `config/`: default configuration
- `data/`: base spreadsheet and local metadata
- `assets/`: icons/images
- `packaging/`: build/installer/release scripts
- `artifacts/`: intermediate build outputs
- `release/`: final distributable artifacts

## Version history

See:

- `CHANGELOG.md`
