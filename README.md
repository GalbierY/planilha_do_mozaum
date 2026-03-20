# AS Local (MVP)

GUI local para evoluir a planilha `data/AssistenteSocial.xlsx` em um sistema (estilo e-SUS, só que focado na AS), com metadados de cadastro (`created_at` / `updated_at`) e importação idempotente.

## Como rodar (Windows)

- Duplo clique: `start_gui.cmd`
- Ou via terminal:
  - `py -3 gui.py`
- VS Code:
  - Abra a pasta e pressione `F5` (config em `.vscode/launch.json`)

## Onde ficam os dados

- A planilha base: `data/AssistenteSocial.xlsx`
- O “banco” local (JSON): `data/metadata/as_db.json` (ignorado pelo git)

## Próximos passos (quando você quiser)

- Login/usuários do sistema (operadores) e trilha de auditoria (quem alterou o quê)
- Mais entidades (ex.: casos judiciais, atendimentos por data, anexos)
- Migração de JSON → SQLite (sem mudar a GUI), mantendo o mesmo contrato de repositório
