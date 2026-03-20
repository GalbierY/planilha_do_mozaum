# Changelog

## v0.1.0 - 2026-03-20

- GUI local (Tkinter) com `bootstrap.py` para criar venv e instalar dependências.
- Modelo de dados em JSON: `Criança` + múltiplos `Atendimentos` por criança (com data/hora, profissional, resultado, texto de atendimento e VD).
- Aba `Histórico` com criação e **edição** de atendimentos, anexos por atendimento e timeline em ordem cronológica.
- Busca e filtros por escola/idade/período e flags (tem atendimento/tem VD) + full-text no texto de atendimento/VD.
- Aba `Estatísticas`, aba `Relatórios` (exportar CSV/PDF e imprimir), `Backup/Restore` (zip do banco + anexos).
- Login simples (admin/editor/viewer) e auditoria local (log de alterações).
- Auto-update via git (banner + `git pull --ff-only` + reinício opcional).

