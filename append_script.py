
with open("app_import_snippet.py", "r", encoding="utf-8") as f_src:
    content = f_src.read()

with open("app.py", "a", encoding="utf-8") as f_dest:
    f_dest.write("\n" + content)

print("Conteúdo anexado com sucesso!")
