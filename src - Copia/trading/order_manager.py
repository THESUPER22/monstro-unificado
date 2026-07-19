import MetaTrader5 as mt5
from datetime import datetime, timedelta
import logging
from config.settings import SYMBOL, MAGIC_NUMBER, TRAILING_ATIVO, TRAILING_DISTANCIA

class OrderManager:
    def __init__(self, symbol=SYMBOL):
        self.symbol = symbol
        self.ticket_atual = None
        self.posicao_aberta = False
        
    def obter_tipo_posicao_str(self, pos_type):
        """Converte o tipo de posição para string."""
        if pos_type == mt5.POSITION_TYPE_BUY:
            return "BUY"
        elif pos_type == mt5.POSITION_TYPE_SELL:
            return "SELL"
        return "UNKNOWN"
    
    def executar_ordem(self, action, lots=1.0, sl=None, tp=None):
        """Executa uma ordem de compra ou venda."""
        tipo = mt5.ORDER_TYPE_BUY if action == 'BUY' else mt5.ORDER_TYPE_SELL
        
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            logging.warning("Não foi possível obter informações do tick.")
            return None
            
        preco = tick.ask if action == 'BUY' else tick.bid
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            logging.warning("⚠️ symbol_info indisponível.")
            return None
            
        # Correção do volume
        lote_minimo = symbol_info.volume_min
        lote_passos = symbol_info.volume_step
        lote_corrigido = round(max(lots, lote_minimo) / lote_passos) * lote_passos
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "type": tipo,
            "volume": lote_corrigido,
            "price": round(preco, symbol_info.digits),
            "sl": round(sl, symbol_info.digits) if sl else None,
            "tp": round(tp, symbol_info.digits) if tp else None,
            "deviation": 20,
            "magic": MAGIC_NUMBER,
            "comment": "Monstro",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
        
        resultado = mt5.order_send(request)
        if resultado is None:
            logging.error("❌ mt5.order_send retornou None.")
            logging.error(f"❌ Último erro MT5: {mt5.last_error()}")
            return None
            
        if resultado.retcode == mt5.TRADE_RETCODE_DONE:
            self.ticket_atual = resultado.order
            logging.info(f"✅ Ordem {action} executada. Ticket: {resultado.order}")
            return resultado.order
            
        logging.error(f"❌ Retcode: {resultado.retcode} | Comentário: {resultado.comment}")
        return None
    
    def verificar_posicao(self, ticket=None):
        """Verifica se uma ordem específica virou posição."""
        ticket = ticket or self.ticket_atual
        if ticket is None:
            return False
            
        positions = mt5.positions_get(symbol=self.symbol)
        for pos in positions or []:
            if pos.ticket == ticket and pos.magic == MAGIC_NUMBER:
                self.posicao_aberta = True
                return True
        self.posicao_aberta = False
        return False
    
    def obter_lucro_ultima_ordem(self):
        """Obtém o lucro da última ordem fechada."""
        deals = mt5.history_deals_get(
            datetime.now() - timedelta(minutes=5),
            datetime.now()
        )
        if deals is None or len(deals) == 0:
            return 0.0
        ultimo_deal = sorted(deals, key=lambda d: d.time, reverse=True)[0]
        return ultimo_deal.profit
    
    def atualizar_trailing_stop(self):
        """Atualiza o trailing stop de posições abertas."""
        if not TRAILING_ATIVO:
            return
            
        posicoes = mt5.positions_get(symbol=self.symbol)
        if posicoes is None:
            return
            
        for pos in posicoes:
            if pos.magic != MAGIC_NUMBER:
                continue
                
            tick = mt5.symbol_info_tick(self.symbol)
            if tick is None:
                continue
                
            preco_atual = tick.bid if pos.type == mt5.POSITION_TYPE_SELL else tick.ask
            point = mt5.symbol_info(self.symbol).point
            
            if pos.type == mt5.POSITION_TYPE_BUY:
                novo_sl = preco_atual - (TRAILING_DISTANCIA * point)
                if pos.sl is None or novo_sl > pos.sl:
                    self.atualizar_sl(pos.ticket, novo_sl)
            else:
                novo_sl = preco_atual + (TRAILING_DISTANCIA * point)
                if pos.sl is None or novo_sl < pos.sl:
                    self.atualizar_sl(pos.ticket, novo_sl)
    
    def atualizar_sl(self, ticket, novo_sl):
        """Atualiza o stop loss de uma posição."""
        ordem_mod = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": round(novo_sl, mt5.symbol_info(self.symbol).digits),
            "tp": 0,
            "comment": "Trailing SL Monstro"
        }
        
        resultado = mt5.order_send(ordem_mod)
        if resultado and resultado.retcode == mt5.TRADE_RETCODE_DONE:
            logging.info(f"🔐 SL atualizado para {ordem_mod['sl']} (Ticket: {ticket})")
        else:
            logging.warning(f"⚠️ Falha ao atualizar SL. Ticket: {ticket}")
    
    def fechar_todas_posicoes(self):
        """Fecha todas as posições abertas."""
        posicoes = mt5.positions_get(symbol=self.symbol)
        if not posicoes:
            return True
            
        for pos in posicoes:
            if pos.magic != MAGIC_NUMBER:
                continue
                
            tipo_fechamento = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            preco = mt5.symbol_info_tick(self.symbol).bid if tipo_fechamento == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(self.symbol).ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "type": tipo_fechamento,
                "position": pos.ticket,
                "volume": pos.volume,
                "price": preco,
                "magic": MAGIC_NUMBER,
                "comment": "Fechamento Monstro",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            resultado = mt5.order_send(request)
            if not resultado or resultado.retcode != mt5.TRADE_RETCODE_DONE:
                logging.error(f"❌ Erro ao fechar posição {pos.ticket}")
                return False
                
        return True 