"""
ThreadSafeConfig — Gerenciamento thread-safe de parâmetros operacionais.
Permite atualização dinâmica de configurações sem interromper o robô.
"""
import threading
import json
import os
import time

# Função local para evitar ciclo de import: config_manager → monstro_unificado_v22 → dashboard_routes → config_manager
def _caminho_dados(nome: str) -> str:
    """Retorna caminho absoluto para arquivo de dados.
       Duplicada localmente para quebrar o ciclo de importação."""
    import sys as _sys
    import os as _os
    if getattr(_sys, 'frozen', False):
        if hasattr(_sys, '_MEIPASS'):
            pai = _os.path.dirname(_os.path.dirname(_sys._MEIPASS))
            if _os.path.basename(pai) == 'dist':
                pai = _os.path.dirname(pai)
            if pai and _os.path.isdir(pai) and _os.path.exists(_os.path.join(pai, 'monstro_unificado_v22.py')):
                return _os.path.join(pai, nome)
        return _os.path.join(_os.path.dirname(_sys.executable), nome)
    return _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), nome)

CONFIG_FILE = _caminho_dados("config.json")

# Parâmetros editáveis em tempo real com seus tipos e limites
PARAM_SCHEMA = {
    "sl_points":           {"type": float, "min": 1, "max": 50, "default": 5},
    "tp_points":           {"type": float, "min": 0, "max": 100, "default": 0},
    "sniper_ratio_min":    {"type": float, "min": 1.0, "max": 5.0, "default": 1.2},
    "sniper_volume_min":   {"type": int,   "min": 50, "max": 5000, "default": 400},
    "max_losses_sequencia":{"type": int,   "min": 1, "max": 20, "default": 5},
    "trailing_gatilho":    {"type": float, "min": 1, "max": 50, "default": 3},
    "trailing_distancia":  {"type": float, "min": 0.5, "max": 20, "default": 2},
    "max_spread":          {"type": float, "min": 1, "max": 50, "default": 5},
    "max_loss_diario":     {"type": float, "min": -5000, "max": -10, "default": -500},
    "dol_conf_min":        {"type": float, "min": 0.2, "max": 0.8, "default": 0.4},
    "book_ratio_min":      {"type": float, "min": 1.0, "max": 2.0, "default": 1.3},
}


class ThreadSafeConfig:
    """Config thread-safe com notificação de listeners."""

    def __init__(self):
        self._lock = threading.RLock()
        self._data = {}
        self._listeners = []
        self._change_log = []
        self._load()

    def _load(self):
        """Carrega config do arquivo JSON."""
        try:
            with self._lock:
                if os.path.exists(CONFIG_FILE):
                    # utf-8-sig: tolera BOM no config.json
                    with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
                        self._data = json.load(f)
                else:
                    self._data = {}
        except Exception:
            self._data = {}

    def get(self, key_path: str, default=None):
        """Obtém valor por path pontilhado. Ex: 'risk_management.max_losses_sequencia'"""
        with self._lock:
            keys = key_path.split('.')
            val = self._data
            for k in keys:
                if isinstance(val, dict) and k in val:
                    val = val[k]
                else:
                    return default
            return val

    def get_all(self) -> dict:
        """Retorna cópia snapshot de toda a config."""
        with self._lock:
            return json.loads(json.dumps(self._data))

    def update(self, updates: dict) -> list:
        """
        Atualiza parâmetros em memória (e salva no JSON).
        updates = {"sl_points": 8, "sniper_ratio_min": 1.5, ...}
        Retorna lista de {param, old, new, ok, error}.
        """
        results = []
        with self._lock:
            for key, new_val in updates.items():
                schema = PARAM_SCHEMA.get(key)
                if not schema:
                    results.append({"param": key, "ok": False, "error": "Parâmetro desconhecido"})
                    continue
                try:
                    typed_val = schema["type"](new_val)
                    if typed_val < schema["min"] or typed_val > schema["max"]:
                        results.append({
                            "param": key, "ok": False,
                            "error": f"Fora do range [{schema['min']}, {schema['max']}]"
                        })
                        continue
                except (ValueError, TypeError):
                    results.append({"param": key, "ok": False, "error": "Tipo inválido"})
                    continue

                old_val = self._resolve_path(key)
                self._set_path(key, typed_val)
                self._change_log.append({
                    "param": key, "old": old_val, "new": typed_val,
                    "ts": time.time()
                })
                results.append({"param": key, "old": old_val, "new": typed_val, "ok": True})

                # Notifica listeners
                for cb in self._listeners:
                    try:
                        cb(key, old_val, typed_val)
                    except Exception:
                        pass

            # Salva no disco
            self._save()
        return results

    def register_listener(self, callback):
        """Registra callback(key, old_val, new_val) para mudanças."""
        self._listeners.append(callback)

    def get_change_log(self) -> list:
        with self._lock:
            return list(self._change_log[-50:])

    def _resolve_path(self, key):
        """Resolve caminho simples para valor no config."""
        with self._lock:
            # Mapeamento de chaves flat para paths do JSON
            flat_map = {
                "sl_points": ("risk_management", "sl_points"),
                "tp_points": ("risk_management", "tp_points"),
                "sniper_ratio_min": ("risk_management", "sniper_ratio_min"),
                "sniper_volume_min": ("risk_management", "sniper_volume_min"),
                "max_losses_sequencia": ("risk_management", "max_losses_sequencia"),
                "trailing_gatilho": ("trailing_stop", "gatilho_pontos"),
                "trailing_distancia": ("trailing_stop", "distancia_pontos"),
                "max_spread": ("risk_management", "max_spread_pontos"),
                "max_loss_diario": ("risk_management", "max_loss_diario"),
            }
            if key in flat_map:
                path = flat_map[key]
                val = self._data
                for p in path:
                    if isinstance(val, dict):
                        val = val.get(p, {})
                    else:
                        return None
                return val if val != {} else None
            return self._data.get(key)

    def _set_path(self, key, value):
        """Define valor no config usando path pontilhado."""
        with self._lock:
            flat_map = {
                "sl_points": ("risk_management", "sl_points"),
                "tp_points": ("risk_management", "tp_points"),
                "sniper_ratio_min": ("risk_management", "sniper_ratio_min"),
                "sniper_volume_min": ("risk_management", "sniper_volume_min"),
                "max_losses_sequencia": ("risk_management", "max_losses_sequencia"),
                "trailing_gatilho": ("trailing_stop", "gatilho_pontos"),
                "trailing_distancia": ("trailing_stop", "distancia_pontos"),
                "max_spread": ("risk_management", "max_spread_pontos"),
                "max_loss_diario": ("risk_management", "max_loss_diario"),
            }
            if key in flat_map:
                path = flat_map[key]
                ref = self._data
                for p in path[:-1]:
                    if p not in ref:
                        ref[p] = {}
                    ref = ref[p]
                ref[path[-1]] = value
            else:
                self._data[key] = value

    def _save(self):
        """Salva config no disco."""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass


# Singleton global
_config_instance = None
_config_lock = threading.Lock()


def get_config_manager() -> ThreadSafeConfig:
    global _config_instance
    if _config_instance is None:
        with _config_lock:
            if _config_instance is None:
                _config_instance = ThreadSafeConfig()
    return _config_instance
