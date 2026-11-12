# Proposta ML 23.29 — throttle do clipping + escoras estacionárias

**Status:** proposta documental, **não aplicada**. Preparada em 12/11/2026, após o
fechamento, sem tocar no robô nem no MT5.
**Origem:** ROADMAP **23.29** (diagnóstico do alerta
`[normalizar_dados] ... valores fora de [0,1] foram clipped`).
**Arquivos-alvo (futuro):** `monstro_unificado_v22.py`, `modelo_monstro_wdo_scaler.json`,
`config.json` (`aprendizado.n_features`) e o pipeline de retreino
`retreinar_keras_wdo.py`.
**Regra do projeto:** nada aqui altera entrada, saída, stop, alvo ou filtro.
São duas melhorias de **qualidade de sinal** e **higiene de log**.

---

## 1. Evidência que motivou a proposta

| Item | Valor observado (12/11) |
|---|---|
| Ocorrências do warning | **2.984+** entre 09:15:30 e 11:14:15 (~2,4 s entre cada) |
| 10/11 | 6.072 |
| 06/11 | 4.534 |
| Scaler em produção | `modelo_monstro_wdo_scaler.json`, de **01/08/2026** |
| Faixa de treino das escoras | bid 5060–5141 / ask 5066,5–5148 |
| Preço ao vivo | ~5614–5626 (WDOZ26) |
| Fora da faixa (persistente) | `volatility`, `preco_maior_escora_bid`, `preco_maior_escora_ask` |
| Fora da faixa (intermitente) | `bid_qty`, `ask_qty` |
| Scaler candidato (11/11) | ainda tem **3** fora: `entropia_book` + as 2 escoras absolutas |

**Conclusão:** o alerta é crônico e estrutural, não uma regressão de 12/11.
Refitar o scaler sozinho **não resolve** — o candidato de 11/11 também satura.

---

## 2. T1 — Throttle do warning de clipping

### 2.1 Problema

O warning é emitido a cada predição (~2,4 s). Em ~2 h são ~3 mil linhas.
Isso:

- rotaciona o log e **esconde erro real** (foi o ruído que atrapalhou o
  diagnóstico do `10031` em 11/11);
- não acrescenta informação: o conjunto de features saturadas é quase sempre
  o mesmo;
- não indica **quais** features saturaram, só a contagem.

### 2.2 Proposta

- Emitir no máximo **1 warning a cada 10 minutos**.
- No warning, listar **quais** features saíram da faixa e quantas linhas.
- Entre os avisos, rebaixar para `DEBUG` (contagem apenas).
- O contador global continua existindo; nada é perdido para diagnóstico.

### 2.3 Código proposto (esboço; NÃO aplicar agora)

Âncora atual: `monstro_unificado_v22.py` **L3401–L3408**:

```python
            df[colunas_numericas] = scaler_global.transform(
                df[colunas_numericas])
            antes = df[colunas_numericas].values.copy()
            df[colunas_numericas] = df[colunas_numericas].clip(0.0, 1.0)
            n_clip = int((df[colunas_numericas].values != antes).sum())
            if n_clip > 0:
                logging.warning(f"[normalizar_dados] ... {n_clip} valores fora de [0,1] foram clipped")
            logging.debug(f"[normalizar_dados] Scaler aplicado para predição")
```

Esboço de substituição:

```python
# junto ao scaler_global (topo do módulo)
_ultimo_aviso_clip = 0.0
_INTERVALO_AVISO_CLIP_S = 600.0  # 10 min

# ... no bloco de predição ...
if n_clip > 0:
    agora = time.time()
    if agora - _ultimo_aviso_clip >= _INTERVALO_AVISO_CLIP_S:
        _ultimo_aviso_clip = agora
        fora = []
        for i, col in enumerate(colunas_numericas):
            n_fora = int(((antes[:, i] < 0.0) | (antes[:, i] > 1.0)).sum())
            if n_fora:
                fora.append("%s=%d" % (col, n_fora))
        logging.warning(
            "[normalizar_dados] %d valores fora de [0,1] foram clipped "
            "(features: %s; proximo aviso em %.0f min)",
            n_clip, ", ".join(fora) or "n/d",
            _INTERVALO_AVISO_CLIP_S / 60.0)
    else:
        logging.debug(
            "[normalizar_dados] %d valores clipped (aviso suprimido)", n_clip)
```

### 2.4 Vantagens e riscos

- **Vantagem:** log limpo; o operador vê o problema real sem flood.
- **Vantagem:** o warning passa a dizer **qual** feature saturou.
- **Risco:** nenhum no modelo ou no trade. É puramente logging.
- **Cuidado:** não usar `logging.warning` dentro de loop apertado sem throttle;
  a implementação precisa ser thread-safe o suficiente (o pior caso é logar
  duas vezes, aceitável).

### 2.5 Critério de aceite

- Em 1 sessão de 2 h: **≤ 12 warnings** (1 a cada 10 min), não milhares.
- Cada warning contém a lista de features e a contagem.
- Nenhuma mudança em probabilidade, sinal, ordem, stop ou alvo.
- `pytest` do projeto continua verde.

### 2.6 Veredito

**3 estrelas** — higiene operacional e de diagnóstico; não aumenta lucro
diretamente, mas evita mascarar falhas reais.

---

## 3. T2 — Escoras de preço absoluto → distância relativa

### 3.1 Causa raiz

As features `preco_maior_escora_bid` e `preco_maior_escora_ask` guardam o
**preço absoluto** do nível de maior volume do book. Preço absoluto é
**não-estacionário**: quando o WDO sobe de ~5060 para ~5620, o valor sai da
faixa de treino e o `MinMaxScaler` satura em 0/1. O modelo passa a ver
"1.0" para qualquer nível acima de 5148 — perde a informação.

### 3.2 Descoberta importante: a feature relativa já existe

O código **já calcula** a distância relativa ao preço de referência:

- `monstro_unificado_v22.py` **L2895–L2898**:
  `distancia_maior_escora_bid = abs(preco_referencia - preco_maior_escora_bid)`
- **L2917–L2920**:
  `distancia_maior_escora_ask = abs(preco_maior_escora_ask - preco_referencia)`

E essas duas colunas **já estão** na lista de 22 features
(**L699–L702** e **L3506–L3509**). Ou seja: **não é preciso criar feature
nova**; basta parar de alimentar o modelo com as duas colunas de preço
absoluto e manter as de distância.

### 3.3 Opções

| Opção | O que faz | Prós | Contras | Veredito |
|---|---|---|---|---|
| **A (recomendada)** | Remover `preco_maior_escora_bid/ask` do conjunto; ficar com **20 features**; retreinar modelo + scaler; `n_features=20` | Ataca a causa raiz; sem duplicidade; features estacionárias | Exige retreino e mudança coordenada de modelo/scaler/config | **4 estrelas** |
| B (interim) | Manter 22 colunas, mas sobrescrever as 2 absolutas com as distâncias (duplicando `distancia_*`) | Mantém a forma 22; menor mudança de shape | Duplica informação; scaler novo mesmo assim; pouco ganho | 2 estrelas |
| C (rejeitada) | Refitar só o scaler com dados recentes | Rápido | Não resolve não-estacionariedade; candidato de 11/11 ainda tem 3 fora | **1 estrela** |

> **Recomendação:** opção **A**, mas **somente junto com o retreino** e atrás
> dos gates da seção 3.5. Não misturar modelo antigo (22 features) com scaler
> novo (20) nem o contrário.

### 3.4 Âncoras exatas para a futura implementação

| O quê | Onde |
|---|---|
| Lista de features do CSV/treino | `monstro_unificado_v22.py` **L699–L702** |
| Lista usada em `preparar_dados` | **L3506–L3509** |
| Construção das escoras e distâncias | **L2890–L2923** |
| `preparar_dados` (monta o DataFrame) | **L3771–L3790** |
| Normalização/clipping | **L3351–L3413** (warning em L3401–L3408) |
| Config do modelo | `config.json` → `aprendizado.n_features` (hoje **22**) |
| Scaler de produção | `modelo_monstro_wdo_scaler.json` (01/08/2026) |
| Modelo de produção | `modelo_monstro_wdo.h5` / `.keras` |
| Retreino/validação | `retreinar_keras_wdo.py` (read-only) |

### 3.5 Protocolo de retreino (não negociável)

1. Só treinar com **≥ 30 trades reais** com book completo.
2. Validação com **≥ 10** trades.
3. Promover somente se:
   - **AUC > 0,55**;
   - **acurácia > baseline + 0,03**;
   - **holdout ≥ 30**;
   - e o modelo continuar em **paper** (nunca direto em real).
4. Salvar modelo e scaler **juntos**, com o mesmo `n_features` e a mesma
   lista de features.
5. `REPLAY_MAX=256` no treino.
6. Registrar no ROADMAP o antes/depois (AUC, acurácia, baseline, n).

### 3.6 Critério de aceite

- Com o novo conjunto de 20 features, em **5 sessões**:
  - nenhuma feature persistente fora da faixa (o clipping, se aparecer, vem
    só de `bid_qty/ask_qty` intermitente);
  - `volatility` e as escoras não saturam mais.
- Gates da seção 3.5 atendidos.
- Nenhuma mudança de lógica de trade; só features + modelo + scaler.
- Relatório de retreino anexado ao ROADMAP.

### 3.7 Riscos

- **Modelo/scaler acoplados:** trocar um sem o outro quebra a predição.
- **CSV histórico:** as colunas absolutas continuam existindo no CSV; a
  remoção é só na lista usada para treino/predição. Não apagar histórico.
- **Dados de julho:** o corpus offline (5.405) é de regime de preço diferente;
  não usar sozinho para validar a mudança.
- **Amostra pequena:** 4 trades reais hoje; o gate de 30 protege contra
  overfitting. Até lá, a mudança fica **bloqueada**.
- **Shadow Model A:** não é afetado (features e scaler próprios).

### 3.8 Veredito

**4 estrelas** — é a correção estrutural da causa raiz e tende a melhorar a
qualidade do sinal; depende do retreino com amostra suficiente. Enquanto não
houver ≥ 30 trades, fica como proposta, não como código em produção.

---

## 4. O que NÃO fazer

- **Não** refitar o scaler isoladamente (opção C, 1 estrela).
- **Não** promover o modelo candidato de 11/11: ele também tem 3 features
  fora da faixa e não passou pelos gates.
- **Não** aplicar nada durante o pregão ou com posição aberta.
- **Não** alterar entrada/saída/stop/alvo/filtros por causa desta proposta.
- **Não** apagar o histórico do WIN$ nem o CSV antigo.

---

## 5. Checklist de implementação futura

- [ ] Confirmar ≥ 30 trades reais com book completo.
- [ ] Rodar `retreinar_keras_wdo.py` com o conjunto de 20 features (opção A).
- [ ] Comparar AUC/acurácia contra o baseline no mesmo holdout.
- [ ] Salvar modelo + scaler juntos; atualizar `n_features=20`.
- [ ] Rodar 5 sessões em paper; conferir clipping e sinais.
- [ ] Só então avaliar promoção (e ainda assim, paper primeiro).
- [ ] Registrar tudo no ROADMAP (antes/depois, gates, decisão).

---

## 6. Rollback

- Modelo/scaler antigos ficam preservados em
  `modelo_monstro_wdo.h5.backup_20261112` e no histórico do git.
- Reverter `config.json` (`n_features=22`) e restaurar os dois arquivos do
  modelo/scaler do commit anterior.
- A mudança de features é isolada em lista + `preparar_dados`; não há migração
  de estado nem de banco.
