# SAS 🥰 | Civitas

GUI local para evoluir a planilha `data/AssistenteSocial.xlsx` em um sistema (estilo e-SUS, só que focado na AS), com metadados de cadastro (`created_at` / `updated_at`) e importação idempotente.

## Como rodar (Windows)

- Duplo clique: `start_gui.cmd` (cria venv e instala deps automaticamente)
- Ou via terminal:
  - `py -3 bootstrap.py` (idem)
- VS Code:
  - Abra a pasta e pressione `F5` (config em `.vscode/launch.json`)

## Distribuir (Windows, sem Python instalado)

Para o usuário final não precisar de Python, gere um `.exe` (PyInstaller) e opcionalmente um instalador (Inno Setup).

- Gerar app (`artifacts/pyinstaller-dist/SAS Civitas/`):
  - `GERAR_EXE.cmd` (atalho) ou `packaging/build_exe.cmd`
- Gerar instalador (`artifacts/inno-output/SAS Civitas - Instalador.exe`):
  - Instale o Inno Setup (precisa do `iscc.exe` no PATH)
  - `GERAR_INSTALADOR.cmd` (atalho) ou `packaging/build_installer.cmd`

### Onde ficam os dados (build instalada)

O app salva tudo em:

- `%LOCALAPPDATA%\\SAS Civitas\\UserData\\`
  - `config\\config.json`
  - `data\\metadata\\as_db.json`
  - `data\\attachments\\`, `data\\backups\\`, `data\\exports\\`

### Preparar para commit (opcional)

Se vocÃª quiser **versionar os binÃ¡rios** no git, use:

- `packaging/preparar_release.cmd` (copia para `release/` e gera `SHA256SUMS.txt`)

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

## Ícone

- Se existir `assets/icon.ico` ou `assets/icon.png`, o app usa esse arquivo como ícone da janela.
- Alternativa: `icon.ico` / `icon.png` na raiz.

## Atalho com ícone (parecer “app”)

Não dá para “colocar ícone dentro do `.cmd`” (o Windows usa o ícone padrão do tipo de arquivo). O jeito certo é criar um atalho com ícone.

- Criar atalho no Desktop e Menu Iniciar:
  - `py -3 install_shortcut.py`
  - Obs.: o nome do arquivo do atalho não pode conter `|` no Windows; o script sanitiza automaticamente.

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
  - `git commit -m "v1.0.0"`
- Tag:
  - `git tag -a v1.0.0 -m "Release estável 1.0.0"`
  - `git push --tags`

## Próximos passos (quando você quiser)

- Login/usuários do sistema (operadores) e trilha de auditoria (quem alterou o quê)
- Mais entidades (ex.: casos judiciais, atendimentos por data, anexos)
- Migração de JSON → SQLite (sem mudar a GUI), mantendo o mesmo contrato de repositório
