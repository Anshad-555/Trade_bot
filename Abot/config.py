import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class BotConfig:
    """Production-grade configuration for real trading"""
    
    # ============== API CONFIGURATION ==============
    BINANCE_API_KEY: str = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET: str = os.getenv('BINANCE_API_SECRET', '')
    TESTNET: bool = False  # ⚠️ FALSE = REAL MONEY!
    
    # ============== TRADING PAIRS ==============
    SYMBOL: str = 'BTCUSDT'
    BASE_ASSET: str = 'BTC'
    QUOTE_ASSET: str = 'USDT'
    
    # ============== WEBSOCKET SETTINGS ==============
    ORDERBOOK_DEPTH: int = 20
    TRADE_STREAM_BUFFER: int = 2000
    KLINE_INTERVALS: list = None  # ['1m', '5m', '15m']
    
    def __post_init__(self):
        if self.KLINE_INTERVALS is None:
            self.KLINE_INTERVALS = ['1m', '5m', '15m']
    
    # ============== ORDER FLOW THRESHOLDS ==============
    SPOOF_MIN_SIZE_BTC: float = 50.0
    SPOOF_MAX_LIFETIME_SEC: float = 5.0
    ABSORPTION_RATIO: float = 5.0
    IMBALANCE_THRESHOLD: float = 0.70
    WALL_MIN_SIZE_BTC: float = 100.0
    WALL_DISTANCE_PERCENT: float = 0.5
    
    # ============== MOVING AVERAGE SETTINGS ==============
    EMA_FAST: int = 9
    EMA_MEDIUM: int = 21
    EMA_SLOW: int = 50
    EMA_TREND: int = 200
    
    # ============== VOLUME PROFILE SETTINGS ==============
    VP_LOOKBACK_HOURS: int = 24
    VP_PRICE_BINS: int = 100  # Number of price levels
    VP_VALUE_AREA_PERCENT: float = 70.0  # 70% of volume
    
    # ============== DELTA DIVERGENCE SETTINGS ==============
    DELTA_DIVERGENCE_PERIODS: int = 14
    DELTA_DIVERGENCE_THRESHOLD: float = 0.3  # 30% divergence
    
    # ============== POSITION SIZING (CRITICAL FOR RISK!) ==============
    # Kelly Criterion / Fixed Fractional / Fixed Dollar
    POSITION_SIZING_METHOD: str = 'fixed_percent'  # 'kelly', 'fixed_percent', 'fixed_dollar'
    
    # Fixed Percent Method (RECOMMENDED FOR BEGINNERS)
    RISK_PER_TRADE_PERCENT: float = 1.0  # Risk 1% of account per trade
    
    # Fixed Dollar Method
    FIXED_POSITION_SIZE_USDT: float = 50.0  # Trade $50 per position
    
    # Kelly Criterion Method (Advanced)
    KELLY_WIN_RATE: float = 0.55  # Historical win rate (55%)
    KELLY_RISK_REWARD: float = 2.0  # Average win/loss ratio
    KELLY_FRACTION: float = 0.25  # Use 25% of Kelly (safer)
    
    # Account Protection
    MAX_ACCOUNT_RISK_PERCENT: float = 5.0  # Never risk more than 5% total
    MAX_DAILY_LOSS_PERCENT: float = 3.0  # Stop trading if lose 3% in a day
    MAX_POSITIONS: int = 3  # Maximum concurrent positions
    
    # ============== LEVERAGE & RISK MANAGEMENT ==============
    LEVERAGE: int = 3  # Start LOW! (3x-5x recommended)
    STOP_LOSS_PERCENT: float = 2.0
    TAKE_PROFIT_PERCENT: float = 4.0
    TRAILING_STOP_ENABLED: bool = True
    TRAILING_STOP_PERCENT: float = 1.5
    
    # ============== MARKET CONDITION FILTERS ==============
    MIN_VOLUME_24H_USDT: float = 1000000000  # 1B minimum daily volume
    MIN_VOLATILITY_PERCENT: float = 0.5  # Minimum 0.5% hourly volatility
    MAX_VOLATILITY_PERCENT: float = 10.0  # Maximum 10% hourly volatility
    MIN_SPREAD_BIPS: float = 1.0  # Minimum 1 basis point spread
    MAX_SPREAD_BIPS: float = 50.0  # Maximum 50 basis points spread
    
    # Market Regime Detection
    TREND_THRESHOLD: float = 0.02  # 2% price change = trending
    RANGING_THRESHOLD: float = 0.005  # 0.5% = ranging
    
    # ============== SIGNAL CONFIRMATION ==============
    MIN_SIGNAL_STRENGTH: int = 60  # Minimum confidence to trade
    REQUIRE_TREND_CONFIRMATION: bool = True
    REQUIRE_VOLUME_CONFIRMATION: bool = True
    REQUIRE_ORDERFLOW_CONFIRMATION: bool = True
    
    # ============== LOGGING & MONITORING ==============
    LOG_LEVEL: str = 'INFO'
    LOG_FILE: str = 'orderflow_bot_production.log'
    TELEGRAM_ALERTS: bool = False
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # ============== EMERGENCY CONTROLS ==============
    ENABLE_TRADING: bool = True  # Master switch
    EMERGENCY_STOP: bool = False  # Set to True to immediately close all positions