import sys, os, json, warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

ERROS = []

print("=" * 52)
print("   SANITY CHECK - MONSTRO V22 WDO")
print("=" * 52)

# 1. config.json (n_features em qualquer nivel)
def _buscar_nf(obj):
    if isinstance(obj, dict):
        if 'n_features' in obj:
            return obj['n_features']
        for v in obj.values():
            r = _buscar_nf(v)
            if r is not None:
                return r
    return None
if os.path.exists('config.json'):
    with open('config.json') as f:
        cfg = json.load(f)
    nf = _buscar_nf(cfg)
    if nf == 22:
        print(f"  [1/4] config.json: n_features={nf}  OK")
    else:
        ERROS.append(f"config.json: n_features={nf}, esperado 22")
else:
    ERROS.append("config.json nao encontrado")

# 2. Scaler JSON (22 colunas)
scaler_path = 'modelo_monstro_wdo_scaler.json'
if os.path.exists(scaler_path):
    with open(scaler_path) as f:
        sc = json.load(f)
    n_cols = len(sc.get('min', []))
    if n_cols == 22:
        print(f"  [2/4] Scaler: {n_cols} colunas  OK")
    else:
        ERROS.append(f"Scaler tem {n_cols} colunas, esperado 22")
else:
    ERROS.append(f"{scaler_path} nao encontrado")

# 3. Modelo .h5 (carrega e verifica input shape)
import tensorflow as tf
tf.get_logger().setLevel('ERROR')
model_path = 'modelo_monstro_wdo.h5'
if os.path.exists(model_path):
    try:
        m = tf.keras.models.load_model(model_path, compile=False)
        shape = m.input_shape
        n_feats = shape[-1]
        if n_feats == 22:
            s = os.path.getsize(model_path)
            print(f"  [3/4] Modelo .h5: {n_feats} features, {s//1024} KB, {m.count_params():,} params  OK")
        else:
            ERROS.append(f"Modelo espera {n_feats} features, esperado 22")
    except Exception as e:
        ERROS.append(f"Erro ao carregar .h5: {e}")
else:
    ERROS.append(f"{model_path} nao encontrado")

# 4. Conexao MT5 (opcional)
try:
    import MetaTrader5 as mt5
    if mt5.initialize():
        info = mt5.terminal_info()
        if info:
            print(f"  [4/4] MT5 conectado: {info.name} (build {info.build})  OK")
        mt5.shutdown()
    else:
        print(f"  [4/4] MT5 nao disponivel (inicie via all.bat)  ~")
except:
    print(f"  [4/4] MT5 nao verificado  ~")

print("-" * 52)
if ERROS:
    print(f"  FALHA - {len(ERROS)} erro(s) encontrado(s):")
    for e in ERROS:
        print(f"     - {e}")
    print("=" * 52)
    sys.exit(1)
else:
    print("  TODOS OS CHECKS PASSARAM! Liberando inicializacao...")
    print("=" * 52)
    sys.exit(0)
