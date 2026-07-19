# Projeto Trading Automatizado - Contexto do Agente

## Visão Geral
Este é um projeto de trading automatizado com IA chamado "Monstro", que utiliza machine learning para tomar decisões de trading em tempo real.

## Estrutura Principal
- **monstro_unificado.py**: Script principal do sistema de trading
- **config.json**: Configurações principais do sistema
- **modelo_monstro.h5**: Modelo de IA treinado para decisões de trading
- **dashboard_tempo_real.py**: Interface de monitoramento
- **requirements.txt**: Dependências Python

## Arquivos de Configuração
- `config.json`, `config_v3.json`: Configurações do sistema
- `config_bitcoin.json`: Configuração específica para Bitcoin
- `parametros_ia_saida.json`: Parâmetros de saída da IA

## Scripts de Inicialização
- `iniciar_monstro.bat`: Script principal de inicialização
- `ativar_monstro.bat`: Ativação do sistema
- `dashboard.bat`: Iniciar dashboard

## Logs e Monitoramento
- `monstro.log`: Logs principais do sistema
- `historico_*.csv`: Históricos de operações e contexto
- `decisions.csv`: Decisões tomadas pelo sistema

## Ambiente
- Python com ambiente virtual (.venv)
- Dependências em requirements.txt
- Sistema Windows (arquivos .bat e .ps1)

## Boas Práticas
- Sempre fazer backup do modelo antes de alterações
- Verificar logs antes de modificações críticas
- Testar em ambiente controlado antes de produção
- Manter histórico de decisões para análise

## Comandos Úteis
- Iniciar sistema: `iniciar_monstro.bat`
- Ver logs: `ver_logs.bat`
- Dashboard: `dashboard.bat`
- Testar ambiente: `testar_ambiente.bat`
