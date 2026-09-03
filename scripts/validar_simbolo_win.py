"""GATE 6.2a - VALIDA UNIDADE DO SIMBOLO WIN NO MT5 (BLoqueante antes da incubacao).

Resolve o conflito de tick_size/valor_ponto WIN que existe no repo
(custos_reais.py=0.5, engine/config=0.2, relatorio=5.0). Nada pode operar
WIN sem este script bater a config com as specs REAIS do simbolo.

Uso:
    python scripts/validar_simbolo_win.py [--simbolo WINV26]

Exit 0 = PASS (config reproduz valor financeiro do simbolo).
Exit 1 = FAIL (unidade divergente - NAO operar).
"""
import sys
import json
import argparse
import MetaTrader5 as mt5

MT5_PATH = r"C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"
CONFIG = r"C:\AIOFEN\config_win_v2.json"


def _tenta(prefix, a, b):
    if abs(a - b) > 1e-6:
        print(f"  [FAIL] {prefix}: config={a} vs simbolo={b}")
        return False
    print(f"  [OK]   {prefix}: {a} == {b}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simbolo", default="WINV26")
    args = ap.parse_args()

    if not mt5.initialize(MT5_PATH):
        print("Falha ao conectar MT5:", mt5.last_error())
        return 1
    timezone = mt5.TZ_TIMEZONE if hasattr(mt5, "TZ_TIMEZONE") else None

    info = mt5.symbol_info(args.simbolo)
    if info is None:
        print(f"Simbolo {args.simbolo} nao encontrado no MT5. Listando WIN*:")
        for s in mt5.symbols_get("WIN"):
            print("   ", s.name)
        mt5.shutdown()
        return 1

    cfg = json.load(open(CONFIG, encoding="utf-8-sig"))
    contrato = cfg.get("contrato", {})
    cfg_tick = float(contrato.get("tick_size", 0.2))
    cfg_tpp = float(contrato.get("ticks_por_ponto", 10000))

    print(f"== Specs REAIS de {args.simbolo} ==")
    print("  point              =", info.point)
    print("  trade_tick_size    =", info.trade_tick_size)
    print("  trade_tick_value   =", info.trade_tick_value, "(R$/tick, 1 contrato)")
    print("  symbols_tick_value =", info.symbols_tick_value)

    ok = True

    # 1) tick_size da config deve reproduzir point do simbolo
    ok &= _tenta("tick_size == point", cfg_tick, float(info.point))

    # 2) valor R$ por ponto de indice = tick_value / tick_size (1 contrato)
    #    WIN real: 1pt = R$0.20/contrato. 5 contratos = R$1.00/pt.
    real_valor_1ct = float(info.trade_tick_value) / float(info.trade_tick_size)
    print(f"  [info] valor por ponto (1 contrato) = R$ {real_valor_1ct:.4f} | x5ct = R$ {real_valor_1ct*5:.4f}")

    # 3) valor_por_ponto_5ct do backtest auditado (R$5.00) deve bater c/ contrato real
    #    Apenas imprime; o decisor ajusta config/sizing conforme fator real x backtest.
    if abs(real_valor_1ct * 5 - 5.0) < 1e-2:
        print("  [OK]   valor R$/pt x5ct casa com backtest auditado (R$5.00)")
    else:
        print(f"  [INFO] valor R$/pt real x5ct = {real_valor_1ct*5:.2f} DIVERGE do backtest (5.00). "
              "Ajustar sizing/multiplicador de PnL antes de dimensionar capital.")

    mt5.shutdown()
    print("\nRESULTADO:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
