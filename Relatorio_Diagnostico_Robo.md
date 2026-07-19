# Relatório de Diagnóstico e Plano de Ação para o Robô de Trading

**Autor:** Manus AI
**Data:** 23 de Outubro de 2025
**Base de Análise:** Código-fonte (`monstro_unificado_v2.py`), Documentação (`implemente.txt`), e Dados Históricos (`historico_contexto_win.csv`, `decisions.csv`, `experiencias.json`).

## 1. Sumário Executivo

O robô está em um **ciclo vicioso de perdas** devido a falhas críticas na sua **arquitetura de aprendizado (Reinforcement Learning - RL)** e na **qualidade dos dados** utilizados para o treinamento. O prejuízo de R$1000/dia, totalizando cerca de R$30.000 em 30 dias, é uma consequência direta de um modelo de IA que está sendo alimentado por uma memória de experiências quase que exclusivamente negativa, e que não está sendo treinado com a frequência e o foco necessários para corrigir seus erros.

**A principal falha não é na execução das ordens, mas sim no ciclo de aprendizado.**

## 2. Diagnóstico Detalhado

A análise do código e dos dados históricos revela três problemas centrais, que se retroalimentam:

### A. Falha Crítica na Memória de Experiências (Memória de Aprendizado)

A memória é a base do aprendizado do robô. Se a memória estiver corrompida ou desbalanceada, o modelo de IA aprenderá o comportamento errado.

| Métrica | Histórico de Trades Reais (`historico_contexto_win.csv`) | Memória de Experiências (`experiencias.json`) |
| :--- | :--- | :--- |
| **Total de Experiências** | 1158 | 1000 |
| **Distribuição de Ações** | NAO_AGIU: 81.86% | NAO_AGIU: 95.8% |
| | BUY: 12.43% | BUY: 3.3% |
| | SELL: 5.69% | SELL: 0.9% |
| **Lucro Médio (BUY/SELL)** | BUY: R$-4.24 / SELL: R$-6.67 | BUY: R$-5.00 / SELL: R$-16.67 |
| **Proporção Positivas** | 33.33% de acerto (Trades Reais) | **1.10%** (Experiências com lucro > 0) |

**Conclusão:**
O robô está operando em um ambiente extremamente **hostil** (apenas 33% de acerto), mas o problema mais grave é a **Memória de Experiências** (`experiencias.json`). Apenas **1.10%** das experiências armazenadas são positivas. Isso significa que, a cada treinamento, a IA está aprendendo a partir de 98.9% de exemplos de **fracasso**. A IA não consegue se lembrar de como ganhar porque a memória de sucesso é praticamente inexistente.

### B. Falha no Mecanismo de Treinamento e Frequência

O código do robô indica que o treinamento só ocorre quando o contador de novas experiências atinge um limite (`LIMITE_EXPERIENCIAS_PARA_TREINO`).

1.  **Foco em "NAO_AGIU":** A memória está dominada por ações "NAO_AGIU" (95.8%), que possuem `lucro = 0.0`. O código tenta dar um score positivo (`score_dist = 0.1`) para essas experiências, mas o volume de dados "NAO_AGIU" dilui completamente o impacto das poucas experiências de trading real.
2.  **Lucro Médio Negativo na Memória:** O lucro médio das experiências de BUY/SELL na memória é **negativo**. O robô está aprendendo que **operar é ruim**.
3.  **Correlação Fraca:** A correlação entre as *features* e o *reward* é muito baixa (ex: RSI tem apenas 0.12 de correlação). Isso sugere que o modelo não está conseguindo identificar padrões de sucesso.
    *   **Observação Crítica:** As *features* de profundidade do book (`bid_qty`, `ask_qty`, `entropia_book`) retornaram `NaN` na correlação, indicando que **não houve variação** nesses dados nos trades reais, ou que o *dataframe* estava corrompido para essas colunas. Isso é um forte indício de que as **novas *features* de profundidade do book** (Melhoria 1) **não estão funcionando** ou não estão sendo registradas corretamente, invalidando o principal diferencial do robô.

### C. Falha no Balanceamento e Confiança

1.  **Desbalanceamento de Decisões:** A IA decide "NADA" em 93.16% das vezes. Isso é esperado devido aos filtros de alta acertividade, mas o robô está operando em trades reais com uma proporção de BUY (12.43%) muito maior que SELL (5.69%), e com lucro médio negativo em ambos.
2.  **Confiança Média Baixa:** A confiança média das decisões de BUY é de apenas **0.502**, o que é um valor muito baixo para um robô que deveria operar apenas em *setups* de alta probabilidade. A confiança média de SELL é um pouco maior (0.626), mas o lucro médio de SELL é o pior (R$-6.67).

## 3. Plano de Ação e Correções Críticas

O plano de ação deve se concentrar em **limpar a memória**, **reforçar o aprendizado positivo** e **garantir a funcionalidade das *features* de profundidade**.

### A. Correções Imediatas (Código)

| ID | Correção | Descrição |
| :--- | :--- | :--- |
| **C1** | **Filtro de Memória (MemoriaExperiencias)** | Alterar a função `carregar_experiencias_do_csv` para **descartar** experiências com `lucro <= 0` ou limitar drasticamente a inclusão de experiências negativas. O robô deve aprender **apenas** com o sucesso. Se a taxa de acerto é 33%, a memória deve ser 100% dos acertos e 0% dos erros, ou no máximo 1:1. **Sugestão:** Carregar apenas experiências onde `reward > 0` para trades reais. |
| **C2** | **Revisão da Feature Engineering** | **Corrigir a coleta e o registro** das *features* de profundidade do book (`bid_qty`, `ask_qty`, `entropia_book`, etc.) na função `salvar_experiencia_csv`. O fato de estarem como `NaN` na correlação do histórico indica que o modelo está sendo treinado com dados incompletos ou constantes. **Verificar se a função `analisar_profundidade_book` está sendo chamada e seus resultados estão sendo corretamente integrados ao `contexto` antes de salvar.** |
| **C3** | **Ajuste do Intervalo de Treinamento** | No `treinar_modelo_inteligente`, **aumentar a frequência de treinamento** (reduzir `LIMITE_EXPERIENCIAS_PARA_TREINO` para 1 ou 2) e **forçar um treinamento inicial** logo após a limpeza da memória (C1). |
| **C4** | **Revisão da Recompensa (Reward)** | O código usa o `reward` diretamente. É crucial garantir que o `reward` seja o **lucro real** da operação e que a função `normalizar_recompensas` esteja funcionando corretamente para dar peso maior aos acertos. |

### B. Plano de Ação (Estratégia)

1.  **Limpeza e Reinício:**
    *   **Executar as correções C1, C2 e C3 no código.**
    *   **Deletar** os arquivos `historico_contexto_win.csv`, `decisions.csv` e `experiencias.json`.
    *   **Reiniciar o robô** para que ele comece a construir uma memória limpa, focada em experiências positivas.

2.  **Monitoramento Focado:**
    *   Monitorar o log para garantir que as *features* de profundidade do book (C2) estejam sendo registradas com valores variáveis e válidos.
    *   Monitorar o `experiencias.json` para confirmar que a proporção de experiências positivas aumentou drasticamente (C1).

3.  **Ajuste Fino:**
    *   Se, após a limpeza, o robô continuar com baixa taxa de acerto, o problema está nos **filtros de entrada** (`filtros_alta_acertividade`) e na **saída inteligente** (`monitorar_posicao_ativa`).

## 4. Próxima Etapa

A correção mais urgente é a **C1 (Filtro de Memória)**, pois é a raiz do problema de aprendizado.

**Ação Proposta:** Realizar a modificação no código para implementar a correção C1, focando em carregar apenas experiências positivas para o treinamento.

### Implementação da Correção C1

A função a ser alterada é `MemoriaExperiencias.carregar_experiencias_do_csv` (linha 5933).

**Antes:**

```python
# ... (código que combina experiencias_reais e experiencias_nao_agiu)
# ...
            # Carrega TODAS as experiências reais (BUY/SELL)
            # Máximo 200 operações reais
            max_reais = min(200, len(experiencias_reais))
            reais_recentes = experiencias_reais.tail(max_reais)
# ...
```

**Depois (Filtro Agressivo - Apenas Acertos):**

```python
# ... (código que combina experiencias_reais e experiencias_nao_agiu)
# ...
            # **CORREÇÃO C1: FILTRO AGRESSIVO - APENAS EXPERIÊNCIAS POSITIVAS**
            experiencias_positivas = experiencias_reais[experiencias_reais['reward'] > 0].copy()

            # Máximo 200 operações reais (agora só positivas)
            max_reais = min(200, len(experiencias_positivas))
            reais_recentes = experiencias_positivas.tail(max_reais)

            # Carrega NAO_AGIU proporcionalmente (3:1 ratio)
            # Máximo 600 NAO_AGIU
            max_nao_agiu = min(600, len(experiencias_nao_agiu))
            nao_agiu_recentes = experiencias_nao_agiu.tail(max_nao_agiu)

            # Combina as experiências (apenas positivas de trade + nao_agiu)
            experiencias_recentes = pd.concat(
                [reais_recentes, nao_agiu_recentes], ignore_index=True)

            logging.info(
                f"📚 Carregamento balanceado (C1 Aplicado): {len(reais_recentes)} operações POSITIVAS reai{len(nao_agiu_recentes)} NAO_AGIU")
# ...
```

Esta alteração garante que a IA seja treinada com uma memória de **sucesso**, que é o que o robô precisa para reverter o ciclo de perdas.

**Próxima Ação:** Implementar a correção C1 no arquivo `monstro_unificado_v2.py`.

***

**Gráfico de Lucro Acumulado (Análise do Histórico)**

O gráfico abaixo mostra a performance acumulada do robô. A linha vermelha representa um *drawdown* constante e acentuado, confirmando a perda diária.

![Gráfico Lucro Acumulado](lucro_acumulado.png)

***
**Referências**
[1] Dados do histórico de contexto: `historico_contexto_win.csv`
[2] Dados da memória de experiências: `experiencias.json`
[3] Código-fonte: `monstro_unificado_v2.py`

