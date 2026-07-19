import re

# Lê o arquivo
with open("mostro _unificado_copia_do_v2.py", "r", encoding="utf-8") as f:
    content = f.read()

# Corrige indentações incorretas - substitui 8 espaços por 4 no início das linhas
lines = content.split('\n')
fixed_lines = []

for line in lines:
    # Se a linha começa com 8 ou mais espaços, reduz para múltiplos de 4
    if line.startswith('        '):  # 8 espaços
        # Conta quantos espaços tem no início
        leading_spaces = len(line) - len(line.lstrip())
        if leading_spaces >= 8:
            # Reduz para múltiplo de 4 mais próximo
            new_indent = ((leading_spaces - 4) // 4) * 4
            if new_indent < 4:
                new_indent = 4
            line = ' ' * new_indent + line.lstrip()
    fixed_lines.append(line)

# Salva o arquivo corrigido
with open("mostro _unificado_copia_do_v2.py", "w", encoding="utf-8") as f:
    f.write('\n'.join(fixed_lines))

print("Indentações corrigidas!")
