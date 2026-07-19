#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para atualizar configurações do Cursor
"""

import json
import os
from pathlib import Path

def atualizar_configuracoes():
    print("🔧 Atualizando configurações do Cursor...")

    # Cria pasta .vscode se não existir
    vscode_dir = Path(".vscode")
    vscode_dir.mkdir(exist_ok=True)

    # Lê configurações existentes
    settings_file = vscode_dir / "settings.json"
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except:
        settings = {}

    # Configurações otimizadas para trading bot
    new_settings = {
        # Preserva configurações existentes importantes
        "CodeGPT.apiKey": settings.get("CodeGPT.apiKey", "CodeGPT Plus Beta"),
        "python.testing.unittestArgs": settings.get("python.testing.unittestArgs", ["-v", "-s", "./venv310", "-p", "*test.py"]),
        "python.testing.pytestEnabled": settings.get("python.testing.pytestEnabled", False),
        "python.testing.unittestEnabled": settings.get("python.testing.unittestEnabled", True),
        "cursor.chat.maxTokens": settings.get("cursor.chat.maxTokens", 8000),
        "cursor.chat.contextLength": settings.get("cursor.chat.contextLength", 16000),
        "editor.maxTokenizationLineLength": settings.get("editor.maxTokenizationLineLength", 10000),
        "editor.largeFileOptimizations": settings.get("editor.largeFileOptimizations", True),

        # Novas configurações para trading bot
        "python.defaultInterpreterPath": "./venv310/Scripts/python.exe",
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

        # Aparência
        "workbench.colorTheme": "Dracula",
        "workbench.iconTheme": "material-icon-theme",

        # Editor
        "editor.fontSize": 14,
        "editor.fontFamily": "Fira Code, Consolas, 'Courier New', monospace",
        "editor.fontLigatures": True,
        "editor.tabSize": 4,
        "editor.wordWrap": "on",
        "editor.rulers": [120],
        "editor.formatOnSave": True,
        "editor.codeActionsOnSave": {
            "source.organizeImports": True
        },

        # Arquivos
        "files.autoSave": "afterDelay",
        "files.autoSaveDelay": 1000,
        "files.encoding": "utf8",
        "files.trimTrailingWhitespace": True,
        "files.insertFinalNewline": True,
        "files.associations": {
            "*.py": "python",
            "*.csv": "csv",
            "*.json": "jsonc",
            "*.log": "plaintext",
            "monstro*.py": "python"
        },
        "files.watcherExclude": {
            "**/venv/**": True,
            "**/venv310/**": True,
            "**/__pycache__/**": True,
            "**/*.log": True,
            "**/*.pkl": True,
            "**/Oracle_JDK-24/**": True,
            "**/llama.cpp/**": True,
            "**/*.h5": True,
            "**/*.keras": True,
            "**/*.bak": True,
            "**/*.backup*": True
        },
        "files.exclude": {
            "**/__pycache__": True,
            "**/*.pyc": True,
            "**/desktop.ini": True
        },

        # Busca
        "search.exclude": {
            "**/venv/**": True,
            "**/venv310/**": True,
            "**/__pycache__/**": True,
            "**/Oracle_JDK-24/**": True,
            "**/llama.cpp/**": True,
            "**/*.h5": True,
            "**/*.keras": True
        },

        # Git
        "git.autofetch": True,
        "git.confirmSync": False,
        "git.enableSmartCommit": True,

        # Jupyter
        "jupyter.askForKernelRestart": False,
        "jupyter.interactiveWindowMode": "perFile",

        # CSV para trading
        "csv-preview.separator": ",",
        "csv-preview.quoteMark": "\"",
        "csv-preview.encoding": "utf8",
        "csv-preview.lineNumbers": True,
        "csv-preview.capitalizeHeaders": True,

        # Idioma português
        "locale": "pt-br",

        # Cursor AI
        "cursor.ai.enabled": True,

        # Performance
        "extensions.autoUpdate": False,
        "telemetry.telemetryLevel": "off"
    }

    # Salva configurações atualizadas
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(new_settings, f, indent=2, ensure_ascii=False)

    print("✅ Configurações do Cursor atualizadas!")

    # Cria launch.json para debug
    launch_file = vscode_dir / "launch.json"
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
                "name": "🔍 Debug Arquivo Atual",
                "type": "python",
                "request": "launch",
                "program": "${file}",
                "console": "integratedTerminal"
            }
        ]
    }

    with open(launch_file, 'w', encoding='utf-8') as f:
        json.dump(launch_config, f, indent=2, ensure_ascii=False)

    print("✅ Configurações de debug criadas!")

    # Cria tasks.json para tarefas
    tasks_file = vscode_dir / "tasks.json"
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
            }
        ]
    }

    with open(tasks_file, 'w', encoding='utf-8') as f:
        json.dump(tasks_config, f, indent=2, ensure_ascii=False)

    print("✅ Tarefas automatizadas criadas!")

    print("\n🎉 CURSOR CONFIGURADO COM SUCESSO!")
    print("📋 Próximos passos:")
    print("1. 🔄 Reinicie o Cursor")
    print("2. 🇧🇷 Confirme idioma português")
    print("3. 🚀 Comece a usar!")

if __name__ == "__main__":
    atualizar_configuracoes()
