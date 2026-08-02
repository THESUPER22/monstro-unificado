# Testes Automatizados (pós-fix Sessão 17)

Testes determinísticos do robô que NÃO exigem MT5 nem mercado aberto.

Execução (Windows PowerShell):
```
venv\Scripts\python.exe tests\testes_pos_fix.py
```

Cobertura (checagens principais):
- Mutex: `CreateMutexW` só dentro de `if __name__ == "__main__"`.
- `sys.exit`: não existem chamadas `sys.exit(` espalhadas (apenas `_sys.exit(0)` no mutex é permitido).
- Entropia: nenhuma comparação em escala `[0,1]` (entropia deve ser escala real ~2.x).
- `parar.txt`: valida que `verificar_parada_gracil()` usa `_caminho_dados("parar.txt")` (caminho absoluto).
- CSVs: valida colunas e que `entropia_book` não está truncada em `[0,1]`.

Fora de escopo (manual/staging): shutdown coordenado (fechar posições + salvar + os._exit) — exige MT5 e ambiente.

Observação sobre CI: o script é compatível com CI leve (não importa TF/MT5), mas o arquivo
`monstro_unificado_v22.py` precisa estar versionado no repo para que o CI tenha algo para ler.
Atualmente `monstro_unificado_v22.py` está untracked no repositório local — versionar antes de ativar CI.
# Testes Automatizados (pós-fix Sessão 17)

Testes determinísticos do robô que **não exigem MT5 nem mercado aberto**
(rodam com o mercado fechado).

## Execução

```bat
venv\Scripts\python.exe tests\testes_pos_fix.py
```

## Cobertura (9 checagens)

| Teste | O que valida |
|-------|--------------|
| Mutex | `CreateMutexW` existe apenas dentro de `if __name__ == "__main__"` (regressão do fix da Sessão 17) |
| sys.exit | Nenhum `sys.exit(` real espalhado — só o `_sys.exit(0)` permitido do mutex no `__main__` |
| Entropia escala | Nenhuma comparação de entropia em escala `[0,1]` (deve ser `2.x` — escala real) |
| parar.txt | Shutdown usa `_caminho_dados("parar.txt")` (caminho absoluto), não relativo |
| CSV colunas | `decisions_wdo.csv` e `historico_contexto_wdo.csv` com as colunas esperadas |
| CSV dados | Entropia **não** truncada em `[0,1]` e `bid_qty` com valores reais |

## Fora de escopo (exige MT5 + ambiente)

- **Shutdown coordenado completo** (fechar posições + salvar modelo/experiências + `os._exit(0)`)
  — validar **manualmente** em staging conforme o `CHECKLIST DE TESTES PÓS-FIX` no ROADMAP.

## Importante para CI (futuro)

O script lê `monstro_unificado_v22.py` como **texto** (não importa o módulo), então um
CI leve é viável. **Bloqueador:** `monstro_unificado_v22.py` ainda não está versionado
(untracked) — o CI rodaria num clone sem o arquivo principal. Versionar o v22 antes de
habilitar GitHub Actions.
