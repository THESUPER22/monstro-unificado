#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 CONFIGURADOR AUTOMÁTICO DO VSCODE PARA PROJETO DE TRADING BOT
Configura VSCode totalmente em português e instala extensões necessárias
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
    print(f"   Executando: {comando}")

    try:
        if platform.system() == "Windows":
            # Para Windows, usa shell=True e cmd
            result = subprocess.run(comando, shell=True, capture_output=True, text=True, encoding='utf-8')
        else:
            # Para Linux/Mac
            result = subprocess.run(comando.split(), capture_output=True, text=True)

        if result.returncode == 0:
            print(f"   ✅ Sucesso!")
            if result.stdout:
                print(f"   📝 Output: {result.stdout.strip()}")
        else:
            print(f"   ❌ Erro: {result.stderr}")

    except Exception as e:
        print(f"   ❌ Erro ao executar: {e}")

def obter_caminho_vscode():
    """Obtém o caminho do VSCode conforme o OS."""
    system = platform.system()

    if system == "Windows":
        return "code"
    elif system == "Darwin":  # macOS
        return "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
    else:  # Linux
        return "code"

def instalar_extensoes_vscode():
    """Instala todas as extensões necessárias para o projeto."""
    print("🚀 INSTALANDO EXTENSÕES DO VSCODE...")

    # Lista de extensões essenciais para trading bot
    extensoes = [
        # Português
        "MS-CEINTL.vscode-language-pack-pt-BR",

        # Python essencial
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-python.debugpy",
        "ms-python.black-formatter",
        "ms-python.isort",
        "ms-python.flake8",

        # Jupyter/Data Science
        "ms-toolsai.jupyter",
        "ms-toolsai.jupyter-keymap",
        "ms-toolsai.jupyter-renderers",
        "ms-toolsai.vscode-jupyter-cell-tags",
        "ms-toolsai.vscode-jupyter-slideshow",

        # Git
        "eamodio.gitlens",
        "GitHub.vscode-pull-request-github",
        "GitHub.copilot",

        # Markdown e documentação
        "yzhang.markdown-all-in-one",
        "DavidAnson.vscode-markdownlint",
        "bierner.markdown-mermaid",

        # JSON/YAML
        "ms-vscode.vscode-json",
        "redhat.vscode-yaml",

        # Docker (caso use containers)
        "ms-vscode-remote.remote-containers",
        "ms-azuretools.vscode-docker",

        # Ferramentas úteis
        "ms-vscode.vscode-icons",
        "PKief.material-icon-theme",
        "ms-vscode.Theme-TomorrowKit",
        "dracula-theme.theme-dracula",

        # Produtividade
        "streetsidesoftware.code-spell-checker",
        "streetsidesoftware.code-spell-checker-portuguese-brazil",
        "aaron-bond.better-comments",
        "alefragnani.project-manager",
        "formulahendry.auto-rename-tag",
        "bradlc.vscode-tailwindcss",
        "ms-vscode.vscode-typescript-next",

        # Para trading/finance
        "ms-vscode.vscode-csv",
        "mechatroner.rainbow-csv",
        "RandomFractalsInc.vscode-data-preview",

        # SQLite (para logs e dados)
        "alexcvzz.vscode-sqlite",

        # REST Client (para APIs)
        "humao.rest-client",

        # Live Server (para dashboard web)
        "ritwickdey.LiveServer",

        # Formatação e linting
        "ms-python.autopep8",
        "charliermarsh.ruff",
        "ms-python.mypy-type-checker",

        # Temas e ícones extras
        "zhuangtongfa.Material-theme",
        "Equinusocio.vsc-community-material-theme",
        "vscode-icons-team.vscode-icons",

        # Ferramentas de desenvolvimento
        "ms-vscode.vscode-github-issue-notebooks",
        "ms-vscode.remote-explorer",
        "ms-vscode.remote-ssh",

        # Para trabalhar com APIs e HTTP
        "ms-vscode.vscode-restclient",
        "Postman.postman-for-vscode",

        # Terminal melhorado
        "ms-vscode.powershell",

        # Controle de versão
        "mhutchie.git-graph",
        "donjayamanne.githistory",

        # Snippets úteis
        "ms-python.python-snippets",
        "cstrap.flask-snippets",
        "wholroyd.jinja"
    ]

    vscode_path = obter_caminho_vscode()

    for extensao in extensoes:
        comando = f"{vscode_path} --install-extension {extensao}"
        executar_comando(comando, f"Instalando {extensao}")

    print("\n✅ TODAS AS EXTENSÕES FORAM INSTALADAS!")

def criar_configuracao_vscode():
    """Cria configuração otimizada do VSCode."""
    print("\n🔧 CRIANDO CONFIGURAÇÕES DO VSCODE...")

    # Cria pasta .vscode se não existir
    vscode_dir = Path(".vscode")
    vscode_dir.mkdir(exist_ok=True)

    # Configurações do workspace
    settings = {
        "python.defaultInterpreterPath": "./venv/Scripts/python.exe" if platform.system() == "Windows" else "./venv/bin/python",
        "python.formatting.provider": "black",
        "python.formatting.blackArgs": ["--line-length=120"],
        "python.linting.enabled": True,
        "python.linting.pylintEnabled": False,
        "python.linting.flake8Enabled": True,
        "python.linting.flake8Args": ["--max-line-length=120"],
        "python.analysis.autoImportCompletions": True,
        "python.analysis.typeCheckingMode": "basic",
        "python.terminal.activateEnvironment": True,

        # Configurações gerais
        "workbench.colorTheme": "Dracula",
        "workbench.iconTheme": "material-icon-theme",
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

        # Terminal
        "terminal.integrated.fontSize": 13,
        "terminal.integrated.fontFamily": "Fira Code, Consolas",
        "terminal.integrated.shell.windows": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",

        # Arquivos
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
            "*.log": "plaintext"
        },

        # Git
        "git.autofetch": True,
        "git.confirmSync": False,
        "git.enableSmartCommit": True,
        "gitlens.advanced.messages": {
            "suppressCommitHasNoPreviousCommitWarning": True
        },

        # Jupyter
        "jupyter.askForKernelRestart": False,
        "jupyter.interactiveWindowMode": "perFile",

        # Extensões específicas
        "csv-preview.separator": ",",
        "csv-preview.quoteMark": "\"",
        "csv-preview.encoding": "utf8",

        # Configurações específicas para trading
        "python.analysis.extraPaths": [
            "./src",
            "./lib",
            "./modules"
        ],
        "python.envFile": "${workspaceFolder}/.env",

        # Configurações de segurança
        "security.workspace.trust.enabled": True,
        "security.workspace.trust.startupPrompt": "never",

        # Configurações de performance
        "search.exclude": {
            "**/node_modules": True,
            "**/bower_components": True,
            "**/.git": True,
            "**/.svn": True,
            "**/.hg": True,
            "**/CVS": True,
            "**/.DS_Store": True,
            "**/venv": True,
            "**/__pycache__": True,
            "**/*.pyc": True,
            "**/.pytest_cache": True,
            "**/logs": True,
            "**/*.log": True
        },

        # Configurações de idioma
        "locale": "pt-br"
    }

    # Salva configurações
    with open(vscode_dir / "settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    print("✅ Configurações do VSCode criadas!")

def criar_launch_json():
    """Cria configuração de debug."""
    print("\n🐛 CRIANDO CONFIGURAÇÕES DE DEBUG...")

    vscode_dir = Path(".vscode")
    vscode_dir.mkdir(exist_ok=True)

    launch_config = {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "🤖 Executar Bot Trading",
                "type": "python",
                "request": "launch",
                "program": "${workspaceFolder}/monstro_unificado.py",
                "console": "integratedTerminal",
                "cwd": "${workspaceFolder}",
                "env": {
                    "PYTHONPATH": "${workspaceFolder}"
                },
                "justMyCode": False,
                "args": []
            },
            {
                "name": "🧪 Executar Testes",
                "type": "python",
                "request": "launch",
                "module": "pytest",
                "args": [
                    "tests/",
                    "-v",
                    "--tb=short"
                ],
                "console": "integratedTerminal",
                "cwd": "${workspaceFolder}",
                "env": {
                    "PYTHONPATH": "${workspaceFolder}"
                },
                "justMyCode": False
            },
            {
                "name": "📊 Dashboard Web",
                "type": "python",
                "request": "launch",
                "program": "${workspaceFolder}/dashboard.py",
                "console": "integratedTerminal",
                "cwd": "${workspaceFolder}",
                "env": {
                    "FLASK_ENV": "development",
                    "FLASK_DEBUG": "1"
                }
            },
            {
                "name": "🔍 Debug Atual",
                "type": "python",
                "request": "launch",
                "program": "${file}",
                "console": "integratedTerminal",
                "cwd": "${workspaceFolder}",
                "justMyCode": False
            }
        ]
    }

    with open(vscode_dir / "launch.json", "w", encoding="utf-8") as f:
        json.dump(launch_config, f, indent=2, ensure_ascii=False)

    print("✅ Configurações de debug criadas!")

def criar_tasks_json():
    """Cria tarefas automatizadas."""
    print("\n⚡ CRIANDO TAREFAS AUTOMATIZADAS...")

    vscode_dir = Path(".vscode")
    vscode_dir.mkdir(exist_ok=True)

    tasks_config = {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "🐍 Instalar Dependências",
                "type": "shell",
                "command": "python",
                "args": ["-m", "pip", "install", "-r", "requirements.txt"],
                "group": "build",
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": False,
                    "panel": "shared"
                },
                "problemMatcher": []
            },
            {
                "label": "🧹 Limpar Cache Python",
                "type": "shell",
                "command": "python",
                "args": ["-Bc", "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"],
                "group": "build",
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": False,
                    "panel": "shared"
                }
            },
            {
                "label": "🔧 Formatar Código",
                "type": "shell",
                "command": "python",
                "args": ["-m", "black", ".", "--line-length=120"],
                "group": "build",
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": False,
                    "panel": "shared"
                }
            },
            {
                "label": "📦 Criar Ambiente Virtual",
                "type": "shell",
                "command": "python",
                "args": ["-m", "venv", "venv"],
                "group": "build",
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": False,
                    "panel": "shared"
                }
            },
            {
                "label": "🧪 Executar Testes",
                "type": "shell",
                "command": "python",
                "args": ["-m", "pytest", "tests/", "-v"],
                "group": "test",
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": False,
                    "panel": "shared"
                }
            },
            {
                "label": "🚀 Iniciar Bot",
                "type": "shell",
                "command": "python",
                "args": ["monstro_unificado.py"],
                "group": "build",
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": False,
                    "panel": "shared"
                }
            }
        ]
    }

    with open(vscode_dir / "tasks.json", "w", encoding="utf-8") as f:
        json.dump(tasks_config, f, indent=2, ensure_ascii=False)

    print("✅ Tarefas automatizadas criadas!")

def criar_requirements_txt():
    """Cria arquivo requirements.txt com todas as dependências."""
    print("\n📦 CRIANDO REQUIREMENTS.TXT...")

    requirements = """# 🤖 DEPENDÊNCIAS DO BOT DE TRADING
# Instalação: pip install -r requirements.txt

# Core ML/AI
tensorflow>=2.13.0
keras>=2.13.1
scikit-learn>=1.3.0
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.11.0

# Trading
MetaTrader5>=5.0.45

# Web Framework
Flask>=2.3.0
Flask-CORS>=4.0.0

# Utilities
python-dateutil>=2.8.0
tenacity>=8.2.0
requests>=2.31.0

# Development
pytest>=7.4.0
pytest-cov>=4.1.0
black>=23.0.0
flake8>=6.0.0
isort>=5.12.0
mypy>=1.5.0

# Logging e Monitoring
colorlog>=6.7.0
tqdm>=4.65.0

# Data visualization (opcional)
matplotlib>=3.7.0
seaborn>=0.12.0
plotly>=5.15.0

# Jupyter (opcional)
jupyter>=1.0.0
jupyterlab>=4.0.0
ipykernel>=6.25.0

# Formatação e qualidade de código
autopep8>=2.0.0
pylint>=2.17.0
"""

    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements)

    print("✅ requirements.txt criado!")

def criar_gitignore():
    """Cria .gitignore otimizado para o projeto."""
    print("\n🚫 CRIANDO .GITIGNORE...")

    gitignore_content = """# 🤖 GITIGNORE PARA BOT DE TRADING

# Arquivos de configuração sensíveis
config.ini
secrets.json
.env
*.key
*.pem
*.p12

# Dados sensíveis
*.csv
*.xlsx
*.json
logs/
historico_*.csv
experiencias.json
decisions.csv

# Modelos treinados
*.h5
*.keras
*.pkl
*.joblib
modelo_*

# Cache Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Ambientes virtuais
venv/
env/
ENV/
env.bak/
venv.bak/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Jupyter Notebook
.ipynb_checkpoints
*.ipynb

# pytest
.pytest_cache/
.coverage
htmlcov/

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Logs
*.log
logs/
*.out

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Temporários
*.tmp
*.temp
*.bak
*.backup
"""

    with open(".gitignore", "w", encoding="utf-8") as f:
        f.write(gitignore_content)

    print("✅ .gitignore criado!")

def criar_estrutura_projeto():
    """Cria estrutura de pastas do projeto."""
    print("\n📁 CRIANDO ESTRUTURA DO PROJETO...")

    pastas = [
        "src",
        "tests",
        "docs",
        "logs",
        "data",
        "models",
        "config",
        "scripts",
        "notebooks",
        "utils"
    ]

    for pasta in pastas:
        Path(pasta).mkdir(exist_ok=True)
        # Cria arquivo __init__.py para pastas Python
        if pasta in ["src", "tests", "utils"]:
            (Path(pasta) / "__init__.py").touch()

    print("✅ Estrutura de pastas criada!")

def main():
    """Função principal."""
    print("🚀 CONFIGURADOR AUTOMÁTICO DO VSCODE PARA TRADING BOT")
    print("=" * 60)

    # Verifica se está no diretório correto
    if not Path("monstro_unificado.py").exists():
        print("❌ Arquivo monstro_unificado.py não encontrado!")
        print("   Execute este script no diretório do seu projeto.")
        return

    try:
        # Executa todas as configurações
        instalar_extensoes_vscode()
        criar_configuracao_vscode()
        criar_launch_json()
        criar_tasks_json()
        criar_requirements_txt()
        criar_gitignore()
        criar_estrutura_projeto()

        print("\n" + "=" * 60)
        print("✅ CONFIGURAÇÃO COMPLETA!")
        print("=" * 60)
        print("🎉 SEU VSCODE ESTÁ CONFIGURADO PARA O PROJETO!")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. Reinicie o VSCode")
        print("2. Selecione 'Português (Brasil)' se aparecer opção de idioma")
        print("3. Execute: python -m venv venv")
        print("4. Ative o ambiente: venv\\Scripts\\activate (Windows) ou source venv/bin/activate (Linux/Mac)")
        print("5. Execute: pip install -r requirements.txt")
        print("6. Configure suas credenciais do MT5")
        print("7. Execute o bot: python monstro_unificado.py")
        print("\n🛠️ ATALHOS ÚTEIS:")
        print("- Ctrl+Shift+P: Paleta de comandos")
        print("- F5: Executar com debug")
        print("- Ctrl+`: Abrir terminal")
        print("- Ctrl+Shift+`: Novo terminal")
        print("- Ctrl+K, Ctrl+S: Atalhos de teclado")

    except Exception as e:
        print(f"❌ Erro durante a configuração: {e}")
        return

if __name__ == "__main__":
    main()
