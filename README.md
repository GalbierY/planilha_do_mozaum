# AS Local (MVP)

GUI local para evoluir a planilha `data/AssistenteSocial.xlsx` em um sistema (estilo e-SUS, só que focado na AS), com metadados de cadastro (`created_at` / `updated_at`) e importação idempotente.

## Como rodar (Windows)

- Duplo clique: `start_gui.cmd`
- Ou via terminal:
  - `py -3 bootstrap.py`
- VS Code:
  - Abra a pasta e pressione `F5` (config em `.vscode/launch.json`)

## Onde ficam os dados

- A planilha base: `data/AssistenteSocial.xlsx`
- O “banco” local (JSON): `data/metadata/as_db.json` (ignorado pelo git)
- Anexos: `data/attachments/` (ignorados pelo git)
- Backups: `data/backups/` (ignorados pelo git)
- Exportações: `data/exports/` (ignorados pelo git)

## Auto-update (git)

- Se `auto_update_enabled` estiver `true` no `config/config.json`, o app checa atualizações periodicamente e mostra um banner para você clicar e atualizar (faz `git pull --ff-only` e oferece reiniciar).

## Funcionalidades (MVP)

- Crianças separadas de Atendimentos (vários por criança) + aba `Histórico`
- Login simples (admin/editor/viewer) + permissões
- Auditoria (aba `Auditoria`) com logs de alterações
- Anexos por atendimento
- Relatórios (CSV/PDF/Imprimir) + filtros básicos
- Backup/Restore (zip do banco + anexos)

## Próximos passos (quando você quiser)

- Login/usuários do sistema (operadores) e trilha de auditoria (quem alterou o quê)
- Mais entidades (ex.: casos judiciais, atendimentos por data, anexos)
- Migração de JSON → SQLite (sem mudar a GUI), mantendo o mesmo contrato de repositório
