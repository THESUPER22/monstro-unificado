import re

# Le o arquivo
with open('monstro_unificado_v2.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Procura e substitui a verificacao problematica
old_pattern = r'if len\(book\) == 0:\s*logging\.error\("❌ Book vazio"\)\s*return False'

new_code = '''if len(book) == 0:
            # Verifica se mercado esta fechado
            agora = datetime.now().time()
            inicio = datetime.strptime("09:00", "%H:%M").time()
            fim = datetime.strptime("18:30", "%H:%M").time()

            if agora < inicio or agora > fim:
                logging.info("🕐 Book vazio: mercado fechado (normal)")
                return True
            else:
                logging.error("❌ Book vazio durante pregao")
                return False'''

# Faz a substituicao
content_new = re.sub(old_pattern, new_code, content,
                     flags=re.MULTILINE | re.DOTALL)

# Salva o arquivo
with open('monstro_unificado_v2.py', 'w', encoding='utf-8') as f:
    f.write(content_new)

print("Correcao aplicada com sucesso!")
