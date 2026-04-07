# Changelog

## v1.2.0 - 2026-04-07

- Hotfix de UI: cor hexadecimal invalida no cabecalho de dialogs corrigida.
- Hotfix de inicializacao: `reload_cache` ajustado para inicializar a lista de escolas corretamente.

## v1.1.1 - 2026-03-28

- Hotfix do sistema de atualizacao para instalacoes via instalador/portable.
- Checagem automatica de update reativada em build empacotado (fallback GitHub Releases).
- Sincronizacao de `app_version` do build para o config do usuario na inicializacao.

## v1.1.0 - 2026-03-28

- UX da interface redesenhado para fluxo mais intuitivo e funcional.
- Tema principal.
- Login recebeu cabecalho visual com asset (`assets/login.png`, `assets/logo.png` ou `assets/icon.png`).
- Ajuste dos dialogs modais para evitar abertura invisivel no fluxo de login.
- Botao `Salvar cadastro` agora cria novo cadastro quando nao ha crianca selecionada.
- Botao `Salvar cadastro` adicionado tambem no painel da direita em `Cadastros`.
- Campo `Nascimento` com mascara automatica `dd/mm/aaaa` (barras inseridas automaticamente).

## v1.0.0 - 2026-03-25

- Release estavel 1.0.0.
- Todas as funcionalidades do MVP validadas e estaveis.
- Sistema de cadastro de criancas completo.
- Gestao de atendimentos com anexos.
- Relatorios e estatisticas funcionais.
- Backup/Restore operacional.
- Auto-update via git implementado.
- Login e auditoria funcionais.

## v0.1.0 - 2026-03-20

- Nome do app: `SAS | Civitas`.
- GUI local (Tkinter) com `bootstrap.py` para criar venv e instalar dependencias.
- Modelo de dados em JSON: `Crianca` + multiplos `Atendimentos` por crianca.
- Aba `Historico` com criacao e edicao de atendimentos, anexos por atendimento e timeline.
- Busca e filtros por escola/idade/periodo e flags (tem atendimento/tem VD) + full-text.
- Aba `Estatisticas`, aba `Relatorios` (exportar CSV/PDF e imprimir), `Backup/Restore`.
- Login simples (admin/editor/viewer) e auditoria local.
- Auto-update via git (banner + `git pull --ff-only` + reinicio opcional).
- Icone da janela via `assets/icon.png`/`assets/icon.ico` (ou `icon.*` na raiz).
- Instalador de atalho com icone: `install_shortcut.py`.
