import os

path = r"menu_handlers.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# We replace the exact string literal containing the text
old_str = 'body="❓ *REQUISITOS Y PREGUNTAS FRECUENTES*\\n\\nElige una opción:",'
new_str = 'body="❓ *REQUISITOS Y PREGUNTAS FRECUENTES*\\n\\nElige una opción, o enviá \'M\' para Menú / \'S\' para Salir:",'

if old_str in content:
    content = content.replace(old_str, new_str)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Replace successful!")
else:
    print("String not found. Perhaps it was already replaced?")
