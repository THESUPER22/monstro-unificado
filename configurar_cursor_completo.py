#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 CONFIGURADOR COMPLETO DO CURSOR PARA TRADING BOT
Configura Cursor totalmente em português com todas as extensões necessárias
"""

import os
import json
import subprocess
import sys
from pathlib import Path
import platform

def executar_comando(comando, descricao=""):
    """Executa comando no terminal com feedback."""
    print(f"🔧 {descricao}")
    try:
        result = subprocess.run(comando, shell=True, capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            print(f"   ✅ Sucesso!")
        else:
            print(f"   ⚠️ Aviso: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

def main():
    print("🚀 CONFIGURADOR COMPLETO DO CURSOR PARA TRADING BOT")
    print("=" * 60)
    print("🇧🇷 Configurando interface em PORTUGUÊS")
    print("🔧 Instalando extensões essenciais")
    print("⚙️ Criando configurações otimizadas")
    print("=" * 60)

    # 📦 EXTENSÕES ESSENCIAIS
    extensoes = [
        # 🇧🇷 PORTUGUÊS
        "MS-CEINTL.vscode-language-pack-pt-BR",

        # 🐍 PYTHON ESSENCIAL
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-python.debugpy",
        "ms-python.black-formatter",
        "ms-python.isort",
        "ms-python.flake8",
        "ms-python.autopep8",
        "charliermarsh.ruff",

        # 📊 DATA SCIENCE & JUPYTER
        "ms-toolsai.jupyter",
        "ms-toolsai.jupyter-keymap",
        "ms-toolsai.jupyter-renderers",

        # 🔧 GIT & VERSIONAMENTO
        "eamodio.gitlens",
        "GitHub.vscode-pull-request-github",
        "mhutchie.git-graph",
        "donjayamanne.githistory",

        # 🎨 TEMAS & ÍCONES
        "ms-vscode.vscode-icons",
        "PKief.material-icon-theme",
        "dracula-theme.theme-dracula",
        "zhuangtongfa.Material-theme",

        # 📈 TRADING & FINANCE
        "ms-vscode.vscode-csv",
        "mechatroner.rainbow-csv",
        "RandomFractalsInc.vscode-data-preview",

        # 📝 MARKDOWN & DOCS
        "yzhang.markdown-all-in-one",
        "DavidAnson.vscode-markdownlint",

        # 🔍 PRODUTIVIDADE
        "streetsidesoftware.code-spell-checker",
        "streetsidesoftware.code-spell-checker-portuguese-brazil",
        "aaron-bond.better-comments",
        "alefragnani.project-manager",

        # 🌐 WEB & API
        "humao.rest-client",
        "ritwickdey.LiveServer",
        "ms-vscode.vscode-restclient",

        # 🗄️ DADOS
        "alexcvzz.vscode-sqlite",

        # 🏷️ JSON/YAML
        "ms-vscode.vscode-json",
        "redhat.vscode-yaml",

        # 🐳 DOCKER (OPCIONAL)
        "ms-azuretools.vscode-docker",

        # 💻 TERMINAL
        "ms-vscode.powershell",

        # 🔧 SNIPPETS
        "cstrap.flask-snippets",
        "wholroyd.jinja"
    ]

    # 🔧 INSTALAR EXTENSÕES
    print("\n🚀 INSTALANDO EXTENSÕES...")
    for i, ext in enumerate(extensoes, 1):
        print(f"   [{i:2d}/{len(extensoes)}] {ext}")
        cmd = f"cursor --install-extension {ext}"
        executar_comando(cmd, "")

    # 📁 CRIAR PASTA .vscode
    print("\n📁 Criando estrutura de configuração...")
    vscode_dir = Path(".vscode")
    vscode_dir.mkdir(exist_ok=True)

    # ⚙️ CONFIGURAÇÕES COMPLETAS
    print("⚙️ Configurando Cursor...")
    settings = {
        # 🐍 PYTHON
        "python.defaultInterpreterPath": "./venv/Scripts/python.exe",
        "python.formatting.provider": "black",
        "python.formatting.blackArgs": ["--line-length=120"],
        "python.linting.enabled": True,
        "python.linting.pylintEnabled": False,
        "python.linting.flake8Enabled": True,
        "python.linting.flake8Args": ["--max-line-length=120"],
        "python.analysis.autoImportCompletions": True,
        "python.analysis.typeCheckingMode": "basic",
        "python.terminal.activateEnvironment": True,
        "python.analysis.extraPaths": ["./src", "./lib", "./modules"],
        "python.envFile": "${workspaceFolder}/.env",
        "python.analysis.completeFunctionParens": True,
        "python.analysis.autoSearchPaths": True,
        "python.analysis.diagnosticMode": "workspace",

        # 🎨 APARÊNCIA
        "workbench.colorTheme": "Dracula",
        "workbench.iconTheme": "material-icon-theme",
        "workbench.productIconTheme": "material-product-icons",

        # ✏️ EDITOR
        "editor.fontSize": 14,
        "editor.fontFamily": "Fira Code, Consolas, 'Courier New', monospace",
        "editor.fontLigatures": True,
        "editor.tabSize": 4,
        "editor.insertSpaces": True,
        "editor.detectIndentation": True,
        "editor.wordWrap": "on",
        "editor.rulers": [120],
        "editor.minimap.enabled": True,
        "editor.minimap.maxColumn": 120,
        "editor.bracketPairColorization.enabled": True,
        "editor.guides.bracketPairs": True,
        "editor.formatOnSave": True,
        "editor.formatOnPaste": True,
        "editor.codeActionsOnSave": {
            "source.organizeImports": True
        },

        # 💻 TERMINAL
        "terminal.integrated.fontSize": 13,
        "terminal.integrated.fontFamily": "Fira Code, Consolas",

        # 📁 ARQUIVOS
        "files.autoSave": "afterDelay",
        "files.autoSaveDelay": 1000,
        "files.encoding": "utf8",
        "files.eol": "\n",
        "files.trimTrailingWhitespace": True,
        "files.insertFinalNewline": True,
        "files.associations": {
            "*.py": "python",
            "*.pyx": "python",
            "*.pyi": "python",
            "*.csv": "csv",
            "*.json": "jsonc",
            "*.log": "plaintext",
            "monstro*.py": "python",
            "*.mq5": "cpp",
            "*.mq4": "cpp"
        },

        # 🔍 BUSCA
        "search.exclude": {
            "**/node_modules": True,
            "**/.git": True,
            "**/venv": True,
            "**/__pycache__": True,
            "**/*.pyc": True,
            "**/.pytest_cache": True,
            "**/logs": True,
            "**/*.log": True,
            "**/modelo_*.h5": True,
            "**/modelo_*.keras": True
        },

        # 🌐 GIT
        "git.autofetch": True,
        "git.confirmSync": False,
        "git.enableSmartCommit": True,

        # 📊 JUPYTER
        "jupyter.askForKernelRestart": False,
        "jupyter.interactiveWindowMode": "perFile",

        # 📈 CSV PARA TRADING
        "csv-preview.separator": ",",
        "csv-preview.quoteMark": "\"",
        "csv-preview.encoding": "utf8",
        "csv-preview.lineNumbers": True,
        "csv-preview.capitalizeHeaders": True,

        # 🔒 SEGURANÇA
        "security.workspace.trust.enabled": True,
        "security.workspace.trust.startupPrompt": "never",

        # 🇧🇷 IDIOMA PORTUGUÊS
        "locale": "pt-br",

        # 🤖 CURSOR AI
        "cursor.ai.enabled": True,
        "cursor.ai.modelPreference": "claude-3-5-sonnet-20241022",

        # 🚀 PERFORMANCE
        "extensions.autoUpdate": False,
        "telemetry.telemetryLevel": "off"
    }

    # 💾 SALVAR CONFIGURAÇÕES
    with open(vscode_dir / "settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    # 🐛 CONFIGURAÇÕES DE DEBUG
    print("🐛 Configurando debug...")
    launch_config = {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "🤖 Executar Monstro Trading Bot",
                "type": "python",
                "request": "launch",
                "program": "${workspaceFolder}/monstro_unificado.py",
                "console": "integratedTerminal",
                "cwd": "${workspaceFolder}",
                "env": {"PYTHONPATH": "${workspaceFolder}"},
                "justMyCode": False
            },
            {
                "name": "🧪 Executar Testes",
                "type": "python",
                "request": "launch",
                "module": "pytest",
                "args": ["tests/", "-v"],
                "console": "integratedTerminal"
            },
            {
                "name": "🔍 Debug Arquivo Atual",
                "type": "python",
                "request": "launch",
                "program": "${file}",
                "console": "integratedTerminal"
            }
        ]
    }

    with open(vscode_dir / "launch.json", "w", encoding="utf-8") as f:
        json.dump(launch_config, f, indent=2, ensure_ascii=False)

    # ⚡ TAREFAS AUTOMATIZADAS
    print("⚡ Configurando tarefas...")
    tasks_config = {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "🐍 Instalar Dependências",
                "type": "shell",
                "command": "python -m pip install -r requirements.txt",
                "group": "build"
            },
            {
                "label": "🚀 Iniciar Bot",
                "type": "shell",
                "command": "python monstro_unificado.py",
                "group": "build"
            },
            {
                "label": "🧹 Limpar Cache",
                "type": "shell",
                "command": "python -Bc \"import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]\"",
                "group": "build"
            },
            {
                "label": "🎨 Formatar Código",
                "type": "shell",
                "command": "python -m black . --line-length=120",
                "group": "build"
            }
        ]
    }

    with open(vscode_dir / "tasks.json", "w", encoding="utf-8") as f:
        json.dump(tasks_config, f, indent=2, ensure_ascii=False)

    # 📝 SNIPPETS PERSONALIZADOS
    print("📝 Criando snippets...")
    snippets = {
        "Trading Log": {
            "prefix": "tlog",
            "body": ["logging.info(f\"📊 ${1:Mensagem}: ${2:valor}\")"],
            "description": "Log formatado para trading"
        },
        "MT5 Order": {
            "prefix": "mt5order",
            "body": [
                "request = {",
                "    \"action\": mt5.TRADE_ACTION_DEAL,",
                "    \"symbol\": SYMBOL,",
                "    \"volume\": ${1:1.0},",
                "    \"type\": mt5.ORDER_TYPE_${2:BUY},",
                "    \"price\": ${3:price},",
                "    \"magic\": MAGIC_NUMBER,",
                "}",
                "resultado = mt5.order_send(request)"
            ],
            "description": "Template MT5 order"
        },
        "Try Trading": {
            "prefix": "trytrade",
            "body": [
                "try:",
                "    ${1:# código}",
                "except Exception as e:",
                "    logging.error(f\"❌ Erro: {e}\")",
                "    ${2:return None}"
            ],
            "description": "Try-except para trading"
        }
    }

    with open(vscode_dir / "python.json", "w", encoding="utf-8") as f:
        json.dump(snippets, f, indent=2, ensure_ascii=False)

    # 📦 REQUIREMENTS.TXT
    print("📦 Criando requirements.txt...")
    requirements = """# 🤖 MONSTRO TRADING BOT - DEPENDÊNCIAS
# Instalação: pip install -r requirements.txt

# ===== CORE ML/AI =====
tensorflow>=2.13.0
keras>=2.13.1
scikit-learn>=1.3.0
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.11.0

# ===== TRADING =====
MetaTrader5>=5.0.45

# ===== WEB =====
Flask>=2.3.0
Flask-CORS>=4.0.0

# ===== UTILITIES =====
python-dateutil>=2.8.0
tenacity>=8.2.0
requests>=2.31.0

# ===== DEVELOPMENT =====
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0
isort>=5.12.0

# ===== VISUALIZATION =====
matplotlib>=3.7.0
plotly>=5.15.0

# ===== JUPYTER =====
jupyter>=1.0.0
ipykernel>=6.25.0
"""

    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements)

    # ✅ FINALIZAÇÃO
    print("\n" + "=" * 60)
    print("✅ CONFIGURAÇÃO COMPLETA DO CURSOR!")
    print("=" * 60)
    print("🎉 SEU CURSOR ESTÁ CONFIGURADO EM PORTUGUÊS!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. 🔄 Reinicie o Cursor")
    print("2. 🇧🇷 Confirme idioma português se solicitado")
    print("3. 🐍 Crie ambiente: python -m venv venv")
    print("4. ⚡ Ative ambiente: venv\\Scripts\\activate")
    print("5. 📦 Instale deps: pip install -r requirements.txt")
    print("6. 🚀 Execute bot: python monstro_unificado.py")

    print("\n🛠️ ATALHOS ÚTEIS:")
    print("- Ctrl+Shift+P: Paleta de comandos")
    print("- F5: Debug")
    print("- Ctrl+`: Terminal")
    print("- Ctrl+K: Cursor AI")
    print("- Ctrl+L: Chat AI")

    print("\n🔧 RECURSOS CONFIGURADOS:")
    print("- ✅ Interface em português")
    print("- ✅ 40+ extensões para Python/Trading")
    print("- ✅ Debug personalizado")
    print("- ✅ Tarefas automatizadas")
    print("- ✅ Snippets para MT5")
    print("- ✅ Formatação automática")
    print("- ✅ Cursor AI otimizado")

    print("\n🎯 PRONTO PARA TRADING! 🚀")

if __name__ == "__main__":
    main()
