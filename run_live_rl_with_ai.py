import json
import pandas as pd
import time
import os
import csv
from datetime import datetime

BOOK_CSV_PATH = "wdo_book_snapshots_1s_6m.csv"
COMMAND_JSON_PATH = os.path.expanduser(
    "~\\AppData\\Roaming\\MetaQuotes\\Terminal\\FB9A56D617EDDDFE29EE54EBEFFE96C1\\MQL5\\Files\\mt5_command.json"
)

# Placeholder para cálculo de P/L; implemente conforme seu ambiente
def calculate_pnl_for_last_trade():
    # TODO: implementar cálculo de P/L da última operação
    return 0.0

# Função de logging seguro
def log_decision(timestamp, action, pnl, feedback):
    try:
        with open('decisions.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, action, pnl, feedback])
    except Exception as e:
        print(f"[Logging Error] {e}")

# Função de decisão baseada no book
def tomar_decisao_baseada_no_book(path_csv):
    try:
        df = pd.read_csv(path_csv)
        if len(df) < 1:
            print("Book vazio ou insuficiente.")
            return None

        ultimo = df.iloc[-1]
        bid = ultimo.get("bid_qty", 0)
        ask = ultimo.get("ask_qty", 0)

        if bid > ask:
            return "BUY"
        elif ask > bid:
            return "SELL"
        else:
            return None
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return None

# Função que escreve o comando JSON para o MT5
def escrever_acao_json(acao, lots=1):
    if not acao:
        print("Sem decisão clara, mantendo comando anterior.")
        return

    comando = {"action": acao, "lots": lots}
    with open(COMMAND_JSON_PATH, "w") as f:
        json.dump(comando, f)
    print(f"Ação decidida: {acao} - salva no mt5_command.json")

# Loop principal
print("🔁 Monstro Iniciado com Decisão Automática Ativa")
while True:
    acao = tomar_decisao_baseada_no_book(BOOK_CSV_PATH)

    # Obter P/L e feedback
    pnl = calculate_pnl_for_last_trade()
    feedback = 1 if pnl > 0 else -1 if pnl < 0 else 0

    # Registrar decisão
    timestamp = datetime.now().isoformat()
    log_decision(timestamp, acao, pnl, feedback)

    # Escrever comando para o MT5
    escrever_acao_json(acao)
    time.sleep(1)  # ciclo de 1 segundo
