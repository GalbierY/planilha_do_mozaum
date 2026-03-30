from pathlib import Path

path = Path('src/as_app/gui.py')
text = path.read_text(encoding='utf-8')
start = text.index('    def _build_cadastros_ui(self, root: ttk.Frame)')
end = text.index('    def on_export_selected(self)', start)
path.write_text(text[:start] + text[end:], encoding='utf-8')
print('removed _build_cadastros_ui from gui.py')
