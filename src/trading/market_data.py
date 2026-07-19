import MetaTrader5 as mt5
import numpy as np
from scipy.stats import entropy
from config.settings import SYMBOL, TIMEFRAME

class MarketData:
    def __init__(self, symbol=SYMBOL, timeframe=TIMEFRAME):
        self.symbol = symbol
        self.timeframe = timeframe
        self.VOLUME_MINIMO_BOOK = 20  # Volume mínimo para filtrar ruídos no book
        
    def obter_nome_vela(self, open_price, close_price):
        """Determina o tipo de vela com base nos preços."""
        if close_price > open_price:
            return "alta"
        elif open_price > close_price:
            return "baixa"
        return "doji"
    
    def calcular_entropia(self, book):
        """Calcula a entropia do book de ofertas."""
        if not book:
            return 0.0
        # Filtra volumes menores que 20 para evitar ruídos
        levels_bid = [level.volume for level in book if level.type == 0 and abs(level.volume) >= self.VOLUME_MINIMO_BOOK]
        levels_ask = [level.volume for level in book if level.type == 1 and abs(level.volume) >= self.VOLUME_MINIMO_BOOK]
        levels = levels_bid + levels_ask
        return entropy(levels) if levels else 0.0
    
    def calcular_rsi(self, prices, period=14):
        """Calcula o RSI (Relative Strength Index)."""
        if len(prices) < period + 1:
            return 50.0
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].mean()
        down = -seed[seed < 0].mean()
        rs = up / down if down != 0 else 0
        return 100.0 - (100.0 / (1.0 + rs)) if rs != 0 else 50.0
    
    def calcular_atr(self, period=14):
        """Calcula o ATR (Average True Range)."""
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, period + 1)
        if rates is None or len(rates) < period + 1:
            return 10  # valor mínimo de fallback
            
        highs = np.array([r[3] for r in rates])
        lows = np.array([r[4] for r in rates])
        closes = np.array([r[2] for r in rates])
        
        trs = np.maximum(highs[1:] - lows[1:], np.abs(highs[1:] - closes[:-1]))
        trs = np.maximum(trs, np.abs(lows[1:] - closes[:-1]))
        atr = np.mean(trs[-period:])
        return atr
    
    def volume_crescente(self, n=4):
        """Verifica se o volume está crescente nos últimos n candles."""
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, n)
        if rates is None or len(rates) < n:
            return False
        volumes = [r['tick_volume'] for r in rates]
        return all(earlier < later for earlier, later in zip(volumes, volumes[1:]))
    
    def obter_dados_mercado(self):
        """Obtém todos os dados relevantes do mercado."""
        book = mt5.market_book_get(self.symbol)
        if book is None or len(book) == 0:
            return None
            
        # Filtra volumes menores que 20 para evitar ruídos
        levels_bid = [level.volume for level in book if level.type == 0 and abs(level.volume) >= self.VOLUME_MINIMO_BOOK]
        levels_ask = [level.volume for level in book if level.type == 1 and abs(level.volume) >= self.VOLUME_MINIMO_BOOK]
        
        bid_qty = sum(levels_bid)
        ask_qty = sum(levels_ask)
        
        tick_info = mt5.symbol_info_tick(self.symbol)
        symbol_info = mt5.symbol_info(self.symbol)
        if tick_info is None or symbol_info is None:
            return None
            
        spread = (tick_info.ask - tick_info.bid) / symbol_info.point
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 2)
        if rates is None or len(rates) < 2:
            return None
            
        open_prices = [rate[1] for rate in rates]
        close_prices = [rate[2] for rate in rates]
        volatility = abs(close_prices[-1] - open_prices[-1])
        candle_type = self.obter_nome_vela(open_prices[-1], close_prices[-1])
        
        rates_rsi = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 100)
        prices = [rate[4] for rate in rates_rsi] if rates_rsi is not None else []
        rsi_14 = self.calcular_rsi(prices)
        
        volume_tick = tick_info.volume
        
        return {
            'bid_qty': bid_qty,
            'ask_qty': ask_qty,
            'spread': spread,
            'volatility': volatility,
            'candle_type': candle_type,
            'entropia_book': self.calcular_entropia(book),
            'rsi_14': rsi_14,
            'volume_tick': volume_tick,
            'book': book
        } 