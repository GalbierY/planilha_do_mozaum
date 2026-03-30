from __future__ import annotations

import unicodedata
from dataclasses import dataclass

DEFAULT_LANGUAGE = "pt-BR"
SUPPORTED_LANGUAGES = ("pt-BR", "en")


def normalize_language(value: str | None) -> str:
    v = (value or "").strip().lower()
    if v in {"en", "en-us", "en-gb", "english"}:
        return "en"
    return DEFAULT_LANGUAGE


def _normalize_text(text: str) -> str:
    raw = (text or "").strip().lower()
    nfkd = unicodedata.normalize("NFKD", raw)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


_PT_BR_TO_EN: dict[str, str] = {
    "Atualizar": "Update",
    "Fechar": "Close",
    "Fluxo simplificado: busque, selecione, atualize e acompanhe o historico em uma tela unica.": "Simplified workflow: search, select, update, and track history in one screen.",
    "Atalhos (F1)": "Shortcuts (F1)",
    "Trocar usuario": "Switch user",
    "Idioma": "Language",
    "Cadastros": "Records",
    "Estatisticas": "Statistics",
    "Historico": "History",
    "Relatorios": "Reports",
    "Auditoria": "Audit",
    "Usuarios": "Users",
    "Novo formulario": "New form",
    "+ Crianca": "+ Child",
    "Salvar cadastro": "Save record",
    "+ Atendimento": "+ Session",
    "Editar atendimento": "Edit session",
    "Anexar arquivo": "Attach file",
    "Backup rapido": "Quick backup",
    "Atalhos: Ctrl+F busca | Ctrl+N novo | Ctrl+S salvar | Ctrl+Enter atendimento": "Shortcuts: Ctrl+F search | Ctrl+N new | Ctrl+S save | Ctrl+Enter session",
    "Pronto.": "Ready.",
    "Atalhos disponiveis": "Available shortcuts",
    "Ctrl+F: focar busca\nCtrl+N: novo formulario\nCtrl+S: salvar cadastro\nCtrl+Enter: novo atendimento\nCtrl+E: editar atendimento\nAlt+1..7: trocar abas": "Ctrl+F: focus search\nCtrl+N: new form\nCtrl+S: save record\nCtrl+Enter: new session\nCtrl+E: edit session\nAlt+1..7: switch tabs",
    "Busca rapida": "Quick search",
    "Nome, escola ou termo do historico:": "Name, school, or history term:",
    "+ Novo cadastro": "+ New record",
    "Limpar filtros": "Clear filters",
    "Dica: Ctrl+F foca a busca e Enter na lista abre o cadastro selecionado.": "Tip: Ctrl+F focuses search and Enter opens the selected record.",
    "Filtros": "Filters",
    "Escola:": "School:",
    "Idade:": "Age:",
    "ate": "to",
    "Com atendimento": "With session",
    "Com VD": "With home visit",
    "Periodo (aaaa-mm-dd):": "Period (yyyy-mm-dd):",
    "Tag:": "Tag:",
    "Tags:": "Tags:",
    "Tag principal": "Primary tag",
    "(Sem tag)": "(No tag)",
    "Lista de criancas": "Children list",
    "Crianca": "Child",
    "Dados da crianca selecionada": "Selected child data",
    "ID:": "ID:",
    "Nome da crianca*:": "Child name*:",
    "Nascimento (dd/mm/aaaa):": "Birth date (dd/mm/yyyy):",
    "Contato:": "Contact:",
    "Endereco:": "Address:",
    "Atendimentos:": "Sessions:",
    "Use a aba Historico para registrar e editar os atendimentos.": "Use the History tab to create and edit sessions.",
    "Criado / atualizado:": "Created / updated:",
    "Mesclar duplicados...": "Merge duplicates...",
    "Exportar selecionados": "Export selected",
    "Gerar relatorio": "Generate report",
    "Importacao": "Import",
    "Atualize os cadastros com a planilha configurada.": "Update records from the configured spreadsheet.",
    "Importar cadastros": "Import records",
    "Selecionar planilha": "Select spreadsheet",
    "Adicionar tag": "Add tag",
    "Selecione ou digite uma tag e clique +": "Select or type a tag and click +",
    "Workflow": "Workflow",
    "Status:": "Status:",
    "Visao geral": "Overview",
    "Atualizar indicadores": "Refresh indicators",
    "Total de criancas": "Total children",
    "Fontes:": "Sources:",
    "Ultima importacao:": "Last import:",
    "Distribuicao por escola": "Distribution by school",
    "Qtd": "Count",
    "Distribuicao por idade": "Distribution by age",
    "Distribuicao por tags": "Distribution by tags",
    "Geracao de relatorios": "Report generation",
    "Tipo de relatorio:": "Report type:",
    "Inicio (aaaa-mm-dd):": "Start (yyyy-mm-dd):",
    "Fim (aaaa-mm-dd):": "End (yyyy-mm-dd):",
    "Use o periodo para limitar resultados. Deixe vazio para considerar todo o historico.": "Use the period to limit results. Leave empty to include all history.",
    "Gerar visualizacao": "Generate preview",
    "Exportar CSV": "Export CSV",
    "Exportar PDF": "Export PDF",
    "Imprimir PDF": "Print PDF",
    "Pre-visualizacao": "Preview",
    "Seguranca dos dados": "Data safety",
    "Crie backups frequentes antes de importacoes ou grandes alteracoes.": "Create frequent backups before imports or major changes.",
    "Fazer backup agora": "Create backup now",
    "Restaurar backup": "Restore backup",
    "Usuários (admin)": "Users (admin)",
    "Usuário": "User",
    "Role": "Role",
    "Ativo": "Active",
    "Senha:": "Password:",
    "Confirmar:": "Confirm:",
    "Salvar usuário": "Save user",
    "Novo": "New",
    "Recarregar": "Reload",
    "Workflow de Importação": "Import workflow",
    "Criança": "Child",
    "Arquivo:": "File:",
    "Última importação:": "Last import:",
    "Importar": "Import",
    "Selecionar Arquivo": "Select file",
    "Limpar Histórico": "Clear history",
    "Contexto atual": "Current context",
    "Crianca selecionada:": "Selected child:",
    "Selecione um item para visualizar o texto do atendimento e os anexos.": "Select an item to view session text and attachments.",
    "Linha do tempo de atendimentos": "Session timeline",
    "Quando": "When",
    "Tipo": "Type",
    "Profissional": "Professional",
    "Resultado": "Result",
    "Registrado por": "Recorded by",
    "Atendimento": "Session",
    "Detalhes do registro": "Record details",
    "Anexos do atendimento": "Session attachments",
    "Adicionar": "Add",
    "Abrir": "Open",
    "Remover": "Remove",
    "Arquivo": "File",
    "Adicionado em": "Added at",
    "Por": "By",
    "Data/hora (ISO):": "Date/time (ISO):",
    "Cancelar": "Cancel",
    "Salvar": "Save",
    "Usuario admin:": "Admin user:",
    "Criar": "Create",
    "Usuario:": "User:",
    "Entrar": "Sign in",
    "Manter:": "Keep:",
    "Mesclar:": "Merge:",
    "Mesclar": "Merge",
    "Selecione o formato de exportação:": "Select export format:",
    "Exportar": "Export",
    "Permissão": "Permission",
    "Exportar": "Export",
    "Erro ao importar": "Import error",
    "Workflow": "Workflow",
    "Restaurar": "Restore",
    "Validação": "Validation",
    "Anexo": "Attachment",
    "Editar": "Edit",
    "Login": "Login",
    "Erro": "Error",
    "Atualização": "Update",
    "Reinício": "Restart",
    "Formato de Exportação": "Export format",
    "Primeiro acesso - Criar admin": "First access - Create admin",
    "Acesso ao sistema": "System access",
    "Bem-vinda(o) ao sistema": "Welcome to the system",
    "Crie o usuario administrador para iniciar.": "Create the administrator user to start.",
    "Entre com seu usuario para continuar.": "Sign in with your user to continue.",
    "Seu perfil é somente leitura.": "Your profile is read-only.",
    "Selecione crianças para exportar.": "Select children to export.",
    "Nenhuma criança encontrada para exportar.": "No children found to export.",
    "Erro ao exportar": "Export error",
    "Erro ao importar": "Import error",
    "Selecione um arquivo na lista.": "Select a file in the list.",
    "Limpar histórico deste arquivo?": "Clear history for this file?",
    "Deseja trocar o idioma para inglês?": "Do you want to switch the language to English?",
    "Deseja trocar o idioma para português (Brasil)?": "Do you want to switch the language to Portuguese (Brazil)?",
    "Idioma atualizado.": "Language updated.",
    "O sistema precisa recarregar textos.": "The app will refresh text labels.",
    "Não foi possível salvar o idioma no config.": "Could not save language to config.",
    "Não foi possível mesclar.": "Could not merge records.",
    "Relatório inválido.": "Invalid report.",
    "Isso substituirá o banco e anexos atuais. Continuar?": "This will replace the current database and attachments. Continue?",
    "Restaurado. O sistema vai reiniciar.": "Restored. The app will restart.",
    "Somente admin.": "Admin only.",
    "Informe o usuário.": "Provide the username.",
    "As senhas não conferem.": "Passwords do not match.",
    "Senha muito curta (mínimo 4).": "Password too short (minimum 4).",
    "Selecione um atendimento no Histórico para anexar.": "Select a session in History to attach files.",
    "Selecione um anexo.": "Select an attachment.",
    "Remover este anexo?": "Remove this attachment?",
    "Selecione uma criança primeiro.": "Select a child first.",
    "Não consegui salvar as alterações.": "Could not save changes.",
    "Usuário inválido ou inativo.": "Invalid or inactive user.",
    "Senha inválida.": "Invalid password.",
    "Muitas tentativas. Fechando.": "Too many attempts. Closing.",
    "URL do instalador não disponível.": "Installer URL is not available.",
    "Baixando instalador...": "Downloading installer...",
    "Falha ao baixar o instalador.": "Failed to download installer.",
    "Instalador baixado. Abrindo...": "Installer downloaded. Opening...",
    "Atualizado com sucesso. Deseja reiniciar agora?": "Updated successfully. Do you want to restart now?",
    "Não consegui reiniciar automaticamente": "Could not restart automatically",
    "Preencha a data/hora.": "Fill in date/time.",
    "Preencha o profissional.": "Fill in professional.",
    "Informe pelo menos Resultado, Atendimento ou VD.": "Provide at least Result, Session, or Home Visit.",
    "Informe usuário e senha.": "Provide username and password.",
    "Informe uma tag.": "Provide a tag.",
    "Tag adicionada": "Tag added",
    "Tag já existe": "Tag already exists",
    "Selecione ou digite uma tag.": "Select or type a tag.",
    "Tag já no cadastro": "Tag already in record",
    "Tag criada e adicionada": "Tag created and added",
    "Tag removida": "Tag removed",
    "Selecione dois registros diferentes.": "Select two different records.",
    "Confirmar mesclagem? Isso não pode ser desfeito facilmente.": "Confirm merge? This cannot be easily undone.",
    "Selecione um atendimento no Histórico para editar.": "Select a session in History to edit.",
    "Atendimento não encontrado.": "Session not found.",
    "Atendimento atualizado": "Session updated",
    "Atendimento registrado": "Session recorded",
    "Anexo adicionado": "Attachment added",
    "Anexo removido": "Attachment removed",
    "Usuário salvo": "User saved",
    "Usuário trocado": "User switched",
    "Filtros limpos.": "Filters cleared.",
    "Mesclado": "Merged",
    "Erro ao importar": "Import error",
    "Histórico limpo": "History cleared",
    "Preencha o nome da criança.": "Fill in the child name.",
    "Preencha a escola.": "Fill in the school.",
    "Relatorio gerado com base nos filtros atuais": "Report generated based on current filters",
    "Erro ao exportar": "Export error",
    "Nenhuma criança": "No child",
    "Importado": "Imported",
    "(nenhuma)": "(none)",
    "Sim": "Yes",
    "Não": "No",
}

_PREFIX_PT_BR_TO_EN: tuple[tuple[str, str], ...] = (
    ("Usuario: ", "User: "),
    ("Exportação CSV concluída: ", "CSV export completed: "),
    ("Exportação JSON concluída: ", "JSON export completed: "),
    ("Exportação Excel concluída: ", "Excel export completed: "),
    ("CSV exportado: ", "CSV exported: "),
    ("PDF exportado: ", "PDF exported: "),
    ("Backup criado: ", "Backup created: "),
    ("Auto-update: erro ao checar: ", "Auto-update: error while checking: "),
    ("Erro ao baixar: ", "Error while downloading: "),
    ("Falha ao atualizar: ", "Update failed: "),
    ("Adicionado (", "Added ("),
    ("Cadastro criado (", "Record created ("),
    ("Cadastro salvo (", "Record saved ("),
    ("Status alterado para ", "Status changed for "),
    ("Criança '", "Child '"),
    ("Nova versão disponível (", "New version available ("),
    ("Atualização disponível (", "Update available ("),
    ("Atualização disponível, mas há commits locais (ahead=", "Update available, but there are local commits (ahead="),
    ("XLSX não encontrado: ", "XLSX not found: "),
    ("Arquivo não encontrado: ", "File not found: "),
)

_NORM_EN: dict[str, str] = {_normalize_text(k): v for k, v in _PT_BR_TO_EN.items()}


@dataclass
class I18N:
    language: str = DEFAULT_LANGUAGE

    def __post_init__(self) -> None:
        self.language = normalize_language(self.language)

    def set_language(self, language: str) -> None:
        self.language = normalize_language(language)

    def tr(self, text: str) -> str:
        if self.language != "en":
            return text
        if not text:
            return text

        if text in _PT_BR_TO_EN:
            return _PT_BR_TO_EN[text]

        norm = _normalize_text(text)
        direct = _NORM_EN.get(norm)
        if direct is not None:
            return direct

        for pt, en in _PREFIX_PT_BR_TO_EN:
            if text.startswith(pt):
                return f"{en}{text[len(pt):]}"
        return text
