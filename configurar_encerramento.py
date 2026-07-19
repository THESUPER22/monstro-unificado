#!/usr/bin/env python3
"""
⚙️ CONFIGURADOR DE ENCERRAMENTO - MONSTRO DAS NEGOCIAÇÕES
Permite alterar os horários de encerramento do robô facilmente
"""

import os
import re
from datetime import datetime

def obter_horarios_atuais():
    """Lê os horários atuais do arquivo monstro_unificado.py"""
    try:
        with open('monstro_unificado.py', 'r', encoding='utf-8') as f:
            conteudo = f.read()

        # Busca os horários usando regex
        horarios = {}
        patterns = {
            'pregao': r'HORARIO_PREGAO = "([^"]*)"',
            'limite_ordens': r'HORARIO_LIMITE_ORDENS = "([^"]*)"',
            'encerramento': r'HORARIO_ENCERRAMENTO = "([^"]*)"',
            'after': r'HORARIO_AFTER = "([^"]*)"',
            'ajuste': r'HORARIO_AJUSTE = "([^"]*)"'
        }

        for nome, pattern in patterns.items():
            match = re.search(pattern, conteudo)
            if match:
                horarios[nome] = match.group(1)

        return horarios
    except Exception as e:
        print(f"❌ Erro ao ler horários: {e}")
        return None

def validar_horario(horario_str):
    """Valida se o horário está no formato correto HH:MM"""
    try:
        datetime.strptime(horario_str, "%H:%M")
        return True
    except ValueError:
        return False

def atualizar_horario(tipo, novo_horario):
    """Atualiza um horário específico no arquivo"""
    if not validar_horario(novo_horario):
        print(f"❌ Horário inválido: {novo_horario}. Use formato HH:MM")
        return False

    try:
        with open('monstro_unificado.py', 'r', encoding='utf-8') as f:
            conteudo = f.read()

        # Mapeia os tipos para as constantes
        constantes = {
            'pregao': 'HORARIO_PREGAO',
            'limite_ordens': 'HORARIO_LIMITE_ORDENS',
            'encerramento': 'HORARIO_ENCERRAMENTO',
            'after': 'HORARIO_AFTER',
            'ajuste': 'HORARIO_AJUSTE'
        }

        if tipo not in constantes:
            print(f"❌ Tipo de horário inválido: {tipo}")
            return False

        # Substitui o horário
        pattern = f'{constantes[tipo]} = "[^"]*"'
        replacement = f'{constantes[tipo]} = "{novo_horario}"'

        novo_conteudo = re.sub(pattern, replacement, conteudo)

        # Salva o arquivo
        with open('monstro_unificado.py', 'w', encoding='utf-8') as f:
            f.write(novo_conteudo)

        print(f"✅ Horário {tipo} atualizado para {novo_horario}")
        return True

    except Exception as e:
        print(f"❌ Erro ao atualizar horário: {e}")
        return False

def configurar_encerramento_personalizado():
    """Permite configurar horários personalizados"""
    print("🛠️ CONFIGURAÇÃO PERSONALIZADA DE ENCERRAMENTO")
    print("="*50)

    print("Escolha o que deseja configurar:")
    print("1. Apenas horário de encerramento")
    print("2. Horário de encerramento + limite de ordens")
    print("3. Configuração completa")

    opcao = input("\nEscolha uma opção (1-3): ").strip()

    if opcao == "1":
        # Apenas encerramento
        novo_encerramento = input("Digite o novo horário de encerramento (HH:MM): ").strip()
        if atualizar_horario('encerramento', novo_encerramento):
            print("✅ Configuração atualizada!")

    elif opcao == "2":
        # Encerramento + limite de ordens
        novo_encerramento = input("Digite o horário de encerramento (HH:MM): ").strip()
        novo_limite = input("Digite o horário limite para ordens (HH:MM): ").strip()

        if atualizar_horario('encerramento', novo_encerramento) and \
           atualizar_horario('limite_ordens', novo_limite):
            print("✅ Configuração atualizada!")

    elif opcao == "3":
        # Configuração completa
        horarios = {
            'pregao': input("Horário de início do pregão (HH:MM): ").strip(),
            'limite_ordens': input("Horário limite para ordens (HH:MM): ").strip(),
            'encerramento': input("Horário de encerramento (HH:MM): ").strip(),
            'after': input("Horário fim after-market (HH:MM): ").strip(),
            'ajuste': input("Horário do ajuste (HH:MM): ").strip()
        }

        sucesso = True
        for tipo, horario in horarios.items():
            if not atualizar_horario(tipo, horario):
                sucesso = False

        if sucesso:
            print("✅ Configuração completa atualizada!")

    else:
        print("❌ Opção inválida!")

def configuracoes_predefinidas():
    """Oferece configurações predefinidas"""
    print("📋 CONFIGURAÇÕES PREDEFINIDAS")
    print("="*40)

    configs = {
        "1": {
            "nome": "Encerramento 18:20 (Padrão)",
            "limite_ordens": "18:15",
            "encerramento": "18:20"
        },
        "2": {
            "nome": "Encerramento 18:00 (Conservador)",
            "limite_ordens": "17:55",
            "encerramento": "18:00"
        },
        "3": {
            "nome": "Encerramento 18:30 (Estendido)",
            "limite_ordens": "18:25",
            "encerramento": "18:30"
        }
    }

    for key, config in configs.items():
        print(f"{key}. {config['nome']}")
        print(f"   Limite ordens: {config['limite_ordens']}")
        print(f"   Encerramento: {config['encerramento']}")
        print()

    opcao = input("Escolha uma configuração (1-3): ").strip()

    if opcao in configs:
        config = configs[opcao]
        if atualizar_horario('limite_ordens', config['limite_ordens']) and \
           atualizar_horario('encerramento', config['encerramento']):
            print(f"✅ Configuração '{config['nome']}' aplicada!")
    else:
        print("❌ Opção inválida!")

def main():
    """Função principal"""
    print("⚙️ CONFIGURADOR DE ENCERRAMENTO - MONSTRO DAS NEGOCIAÇÕES")
    print("="*60)

    # Mostra horários atuais
    horarios = obter_horarios_atuais()
    if horarios:
        print("📅 HORÁRIOS ATUAIS:")
        print(f"   Pregão: {horarios.get('pregao', 'N/A')}")
        print(f"   Limite Ordens: {horarios.get('limite_ordens', 'N/A')}")
        print(f"   Encerramento: {horarios.get('encerramento', 'N/A')}")
        print(f"   After Market: {horarios.get('after', 'N/A')}")
        print(f"   Ajuste: {horarios.get('ajuste', 'N/A')}")

    print("\n🔧 OPÇÕES DE CONFIGURAÇÃO:")
    print("1. Configurações predefinidas")
    print("2. Configuração personalizada")
    print("3. Apenas visualizar horários atuais")
    print("4. Sair")

    opcao = input("\nEscolha uma opção (1-4): ").strip()

    if opcao == "1":
        configuracoes_predefinidas()
    elif opcao == "2":
        configurar_encerramento_personalizado()
    elif opcao == "3":
        print("✅ Horários exibidos acima!")
    elif opcao == "4":
        print("👋 Saindo...")
        return
    else:
        print("❌ Opção inválida!")

    # Pergunta se quer executar teste
    testar = input("\nDeseja testar a configuração? (s/n): ").strip().lower()
    if testar in ['s', 'sim', 'y', 'yes']:
        print("\n🧪 Executando teste...")
        os.system("python teste_encerramento.py")

if __name__ == "__main__":
    main()
