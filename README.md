# AS Local (MVP)

GUI local para evoluir a planilha `data/AssistenteSocial.xlsx` em um sistema (estilo e-SUS, só que focado na AS), com metadados de cadastro (`created_at` / `updated_at`) e importação idempotente.

## Como rodar (Windows)

- Duplo clique: `start_gui.cmd` (cria venv e instala deps automaticamente)
- Ou via terminal:
  - `py -3 bootstrap.py` (idem)
- VS Code:
  - Abra a pasta e pressione `F5` (config em `.vscode/launch.json`)

## Fluxo básico (uso)

1) Aba `Cadastros`: busque/filtre e selecione uma criança na lista
2) Use a barra fixa inferior:
   - `Novo` limpa o formulário
   - `+ Criança` cria uma criança
   - `Salvar` salva alterações na criança selecionada
3) Aba `Histórico`:
   - `+ Atendimento` cria um atendimento/VD (data/hora fica registrada)
   - Selecione um atendimento e use `Editar` (ou duplo clique) para alterar Atendimento/VD
   - Selecione um atendimento e use `Anexar` para vincular arquivos

## Atalhos

- `Ctrl+F`: focar busca
- `Ctrl+N`: novo formulário (criança)
- `Ctrl+S`: salvar criança
- `Ctrl+Enter`: novo atendimento
- `Ctrl+E`: editar atendimento selecionado
- `Alt+1..6`: trocar abas (Cadastros/Estatísticas/Histórico/Relatórios/Backup/Auditoria)

## Onde ficam os dados

- A planilha base: `data/AssistenteSocial.xlsx`
- O “banco” local (JSON): `data/metadata/as_db.json` (configurável em `config/config.json` e ignorado pelo git)
- Anexos: `data/attachments/` (ignorados pelo git)
- Backups: `data/backups/` (ignorados pelo git)
- Exportações: `data/exports/` (ignorados pelo git)

## Auto-update (git)

- Se `auto_update_enabled` estiver `true` no `config/config.json`, o app checa atualizações periodicamente e mostra um banner para você clicar e atualizar (faz `git pull --ff-only` e oferece reiniciar).
- Requer que a pasta seja um clone git com remoto configurado (ex.: GitHub).

## Funcionalidades (MVP)

- Crianças separadas de Atendimentos (vários por criança) + aba `Histórico` (com edição)
- Login simples (admin/editor/viewer) + permissões
- Auditoria (aba `Auditoria`) com logs de alterações
- Anexos por atendimento
- Relatórios (CSV/PDF/Imprimir) + filtros básicos
- Backup/Restore (zip do banco + anexos)

## Release (git)

- Commit:
  - `git add .`
  - `git commit -m "v0.1.0"`
- Tag:
  - `git tag -a v0.1.0 -m "Primeiro release"`
  - `git push --tags`

## Próximos passos (quando você quiser)

- Login/usuários do sistema (operadores) e trilha de auditoria (quem alterou o quê)
- Mais entidades (ex.: casos judiciais, atendimentos por data, anexos)
- Migração de JSON → SQLite (sem mudar a GUI), mantendo o mesmo contrato de repositório
