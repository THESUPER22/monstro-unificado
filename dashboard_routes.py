"""
Dashboard Routes — Blueprint Flask para o Dashboard V2.
Fornece endpoints REST para status, trades, logs, controle e config.
"""
import os
import sys
import time
from flask import Blueprint, render_template, jsonify, request

from config_manager import get_config_manager, PARAM_SCHEMA
import sentinela_fluxo

dashboard_bp = Blueprint('dashboard', __name__)

# Referência ao módulo principal do robô — preenchida via register_main_module()
_main_mod = None
_log_file = None


def register_main_module(mod, log_file=None):
    """Registra o módulo principal do robô para acesso aos globals."""
    global _main_mod, _log_file
    _main_mod = mod
    _log_file = log_file


def _g(name, default=None):
    """Lê um global do módulo principal do robô."""
    if _main_mod is None:
        return default
    return getattr(_main_mod, name, default)


def _caminho_base():
    """Mesma lógica do robô (_caminho_base em monstro_unificado_v22.py).
       Resolve C:\AIOFEN mesmo dentro do PyInstaller (exe em dist\MonstroDashboard)."""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            pai = os.path.dirname(os.path.dirname(sys._MEIPASS))
            if os.path.basename(pai) == 'dist':
                pai = os.path.dirname(pai)
            if pai and os.path.isdir(pai) and os.path.exists(os.path.join(pai, 'monstro_unificado_v22.py')):
                return pai
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _caminho_parar_txt():
    return os.path.join(_caminho_base(), 'parar.txt')


# ============================================================
#  ROTAS
# ============================================================

@dashboard_bp.route('/')
def index():
    return render_template('dashboard.html')


@dashboard_bp.route('/api/status')
def api_status():
    """Status completo do robô para o dashboard."""
    try:
        # Tendência
        tendencia = 'LATERAL'
        tendencia_detail = ''
        ft = _g('filtro_tendencia')
        if ft and hasattr(ft, 'calcular_sma'):
            sma = ft.calcular_sma()
            momentum_pts, momentum_dir = ft.calcular_momentum()
            preco = ft.historico_precos[-1] if ft.historico_precos else 0
            diff = preco - sma if sma > 0 else 0
            if diff > 1.0:
                tendencia = 'ALTA'
            elif diff < -1.0:
                tendencia = 'BAIXA'
            tendencia_detail = f'SMA50: {sma:.2f} | Mom: {momentum_pts:+.1f}pts'

        # Bloqueios
        gb = _g('gerenciador_bloqueio')
        bloqueios_buy = 0
        bloqueios_sell = 0
        if gb and hasattr(gb, 'bloqueio_lado'):
            bloqueios_buy = gb.bloqueio_lado.get('BUY', 0)
            bloqueios_sell = gb.bloqueio_lado.get('SELL', 0)

        # Modo
        mo = _g('modo_operacional')
        modo = 'NORMAL'
        if mo and hasattr(mo, 'modo_atual'):
            modo = mo.modo_atual

        # Posição
        pos = _g('posicao_atual')
        pos_lado = None
        sl_atual = 0
        if pos and hasattr(pos, 'tipo'):
            pos_lado = pos.tipo  # 'BUY' ou 'SELL'
            sl_atual = getattr(pos, 'sl', 0)

        # Lucro
        hl = _g('historico_lucro')
        lucros = hl if isinstance(hl, list) else []
        lucro_dia = sum(lucros) if lucros else 0
        total_ops = len(lucros)
        wins = sum(1 for l in lucros if l > 0)
        losses_count = sum(1 for l in lucros if l < 0)
        win_rate = (wins / total_ops * 100) if total_ops > 0 else 0

        # Experiências
        me = _g('memoria_experiencias')
        total_exp = 0
        if me and hasattr(me, 'experiencias'):
            total_exp = len(me.experiencias)

        # Treinos hoje
        ct = _g('contador_experiencias_novas')
        treinos = ct if isinstance(ct, int) else 0

        # Score e confiança
        score_val = _g('score') or 0
        confianca = min(abs(score_val) * 100, 100)

        # Trades para chart
        trades_list = []
        for i, l in enumerate(lucros):
            trades_list.append({'index': i + 1, 'lucro': round(l, 2)})

        # Sniper %R (cérebro desde 08/08/2026)
        sniper = _g('sniper_supermo')
        sniper_wr = -50.0
        sniper_zona = 0
        if sniper and hasattr(sniper, 'wr_anterior'):
            sniper_wr = getattr(sniper, 'wr_anterior', -50.0)
        if sniper and hasattr(sniper, 'em_zona'):
            sniper_zona = getattr(sniper, 'em_zona', 0)
        sniper_apenas = bool(_g('SNIPER_APENAS', True))
        sniper_supermo_ativo = bool(_g('SNIPER_SUPERMO_ATIVO', True))
        zona_txt = {1: 'SOBREVENDIDO (BUY)', -1: 'SOBRECOMPRADO (SELL)', 0: 'FORA DE ZONA'}.get(sniper_zona, '?')

        return jsonify({
            'thread_ativo': bool(_g('thread_ativo', True)),
            'tendencia': tendencia,
            'tendencia_detail': tendencia_detail,
            'posicao_atual': 'Aberta' if pos else 'Nenhuma',
            'posicao_lado': pos_lado,
            'sl_atual': sl_atual,
            'ticket': _g('ticket_ordem_atual'),
            'lucro_dia': round(lucro_dia, 2),
            'total_operacoes': total_ops,
            'wins': wins,
            'losses': losses_count,
            'win_rate': round(win_rate, 1),
            'score': round(score_val, 4),
            'confianca': round(confianca, 1),
            'total_experiencias': total_exp,
            'treinos_hoje': treinos,
            'modo_operacional': modo,
            'bloqueios_buy': bloqueios_buy,
            'bloqueios_sell': bloqueios_sell,
            'spread': round(_g('spread_atual') or 0, 1),
            'atr': round(_g('atr_atual') or 0, 1),
            'rsi': round(_g('rsi_atual') or 50, 1),
            'ptax': _g('ptax_valor', None),
            'dolar_casado': _g('dolar_casado', None),
            'sniper_bloqueado': bool(_g('sniper_bloqueado', False)),
            'sniper_bloqueio_motivo': _g('sniper_bloqueio_motivo', ''),
            'sniper_apenas': sniper_apenas,
            'sniper_supermo_ativo': sniper_supermo_ativo,
            'sniper_wr': round(float(sniper_wr), 1),
            'sniper_zona': zona_txt,
            'payroll_ativado': bool(_g('payroll_ativado', False)),
            'sentinela': _g('sentinela_cenario', 'NEUTRO'),
            'sentinela_detalhe': _g('sentinela_detalhe', 'Inicializando...'),
            'sentinela_score': _g('sentinela_score', 0),
            'sentinela_atualizado': _g('sentinela_ultima_atualizacao', ''),
            'sentinela_ativo': bool(_g('SENTINELA_ATIVO', True)),
            'trades': trades_list,
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@dashboard_bp.route('/api/ticker')
def api_ticker():
    """Cotações globais para o Market Ticker (DXY, yields, SP500, commodities)."""
    try:
        return jsonify({'ok': True, 'cotacoes': sentinela_fluxo.obter_ticker()})
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)}), 500


@dashboard_bp.route('/api/trades')
def api_trades():
    """Histórico de trades do dia."""
    hl = _g('historico_lucro')
    lucros = hl if isinstance(hl, list) else []
    return jsonify({
        'lucros': lucros,
        'total': len(lucros),
        'soma': round(sum(lucros), 2) if lucros else 0,
    })


@dashboard_bp.route('/api/logs')
def api_logs():
    """Últimas linhas do log. Suporta ?offset=N para polling incremental."""
    if _log_file is None or not os.path.exists(_log_file):
        return jsonify({'lines': [], 'offset': 0})
    try:
        offset = int(request.args.get('offset', 0))
        with open(_log_file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        total = len(lines)
        if offset >= total:
            return jsonify({'lines': [], 'offset': total})
        new_lines = [l.rstrip() for l in lines[offset:offset + 100]]
        return jsonify({'lines': new_lines, 'offset': total})
    except Exception as e:
        return jsonify({'lines': [f'Erro lendo log: {e}'], 'offset': 0})


@dashboard_bp.route('/api/control/<action>', methods=['POST'])
def api_control(action):
    """Controle do robô: stop, restart, start, pause."""
    try:
        if action == 'stop':
            parar_path = _caminho_parar_txt()
            with open(parar_path, 'w') as f:
                f.write('stop')
            return jsonify({'ok': True, 'message': 'Sinal de parada enviado.'})

        elif action == 'restart':
            # Remove parar.txt e mata o processo atual — o agendador ou script wrapper reinicia
            parar_path = _caminho_parar_txt()
            if os.path.exists(parar_path):
                os.remove(parar_path)
            # Mata todos os processos python deste script e reinicia um novo
            import subprocess
            main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'monstro_unificado_v22.py')
            # Agenda o restart após 1s para a resposta HTTP ser enviada
            import threading
            def _kill_and_restart():
                time.sleep(1)
                # Mata processos python antigos (exceto este thread)
                try:
                    subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], capture_output=True)
                except Exception:
                    pass
                time.sleep(1)
                # Inicia novo processo
                subprocess.Popen(['python', main_script], cwd=os.path.dirname(main_script))
            threading.Thread(target=_kill_and_restart, daemon=True).start()
            return jsonify({'ok': True, 'message': 'Reiniciando robô...'})

        elif action == 'start':
            # Inicia um novo processo do robô (sem matar o atual — para quando o robô está parado)
            import subprocess
            main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'monstro_unificado_v22.py')
            parar_path = _caminho_parar_txt()
            if os.path.exists(parar_path):
                os.remove(parar_path)
            # Verifica se já há um processo python rodando
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                                    capture_output=True, text=True)
            count = result.stdout.lower().count('python.exe')
            if count > 1:
                return jsonify({'ok': False, 'message': f'Já existem {count} processos Python rodando.'})
            subprocess.Popen(['python', main_script], cwd=os.path.dirname(main_script))
            return jsonify({'ok': True, 'message': 'Novo processo do robô iniciado.'})

        elif action == 'pause':
            return jsonify({'ok': True, 'message': 'Pausa toggleada via dashboard.'})

        elif action == 'pause':
            return jsonify({'ok': True, 'message': 'Pausa toggleada via dashboard.'})

        else:
            return jsonify({'ok': False, 'erro': f'Acao desconhecida: {action}'}), 400

    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)}), 500


@dashboard_bp.route('/api/config/current')
def api_config_current():
    """Retorna configuração atual editável."""
    cfg = get_config_manager()
    rm = cfg.get('risk_management', {})
    ts = cfg.get('trailing_stop', {})
    return jsonify({
        'sl_points': rm.get('sl_points', 5),
        'tp_points': rm.get('tp_points', 0),
        'sniper_ratio_min': rm.get('sniper_ratio_min', 1.2),
        'sniper_volume_min': rm.get('sniper_volume_min', 400),
        'max_losses_sequencia': rm.get('max_losses_sequencia', 5),
        'trailing_gatilho': ts.get('gatilho_pontos', 3),
        'trailing_distancia': ts.get('distancia_pontos', 2),
        'max_spread': rm.get('max_spread_pontos', 5),
        'max_loss_diario': rm.get('max_loss_diario', -500),
    })


@dashboard_bp.route('/api/config/update', methods=['POST'])
def api_config_update():
    """Atualiza parâmetros em tempo real."""
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({'ok': False, 'erro': 'JSON vazio'}), 400

        cfg = get_config_manager()
        results = cfg.update(data)
        ok = all(r.get('ok', False) for r in results)

        # Aplica nas variáveis globais do robô
        _apply_to_globals(data)

        return jsonify({'ok': ok, 'results': results})
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)}), 500


def _apply_to_globals(cfg_data):
    """Aplica mudanças de config diretamente nas variáveis globais do robô."""
    if _main_mod is None:
        return
    mapping = {
        'sl_points': 'SL_POINTS',
        'tp_points': 'TP_POINTS',
        'sniper_ratio_min': 'SNIPER_RATIO_MIN',
        'sniper_volume_min': 'SNIPER_VOLUME_MIN',
        'max_spread': 'MAX_SPREAD',
    }
    for key, val in cfg_data.items():
        attr = mapping.get(key)
        if attr:
            setattr(_main_mod, attr, val)
