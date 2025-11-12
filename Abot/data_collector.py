import asyncio
import json
from binance import AsyncClient, BinanceSocketManager
from binance.enums import *
from collections import deque
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

class EnhancedDataCollector:
    """
    Enhanced data collector with:
    - Order book (for heat maps)
    - Trade stream (for footprint)
    - Kline data (for moving averages)
    - Account data (for position sizing)
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.client = None
        self.bsm = None
        
        # Order Flow Data
        self.orderbook = {'bids': {}, 'asks': {}}
        self.orderbook_history = deque(maxlen=200)
        self.trades = deque(maxlen=config.TRADE_STREAM_BUFFER)
        
        # Price Action Data
        self.klines = {interval: deque(maxlen=500) for interval in config.KLINE_INTERVALS}
        self.current_price = 0.0
        
        # Account Data
        self.account_balance = 0.0
        self.open_positions = []
        self.daily_pnl = 0.0
        self.daily_trades = 0
        
        # Callbacks
        self.orderbook_callbacks = []
        self.trade_callbacks = []
        self.kline_callbacks = []
        
    async def connect(self):
        """Connect to Binance API"""
        if not self.config.BINANCE_API_KEY or not self.config.BINANCE_API_SECRET:
            raise ValueError("❌ API credentials not set! Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables")
        
        # Create client
        base_url = None if not self.config.TESTNET else 'https://testnet.binancefuture.com'
        
        self.client = await AsyncClient.create(
            api_key=self.config.BINANCE_API_KEY,
            api_secret=self.config.BINANCE_API_SECRET,
            testnet=self.config.TESTNET
        )
        
        self.bsm = BinanceSocketManager(self.client)
        
        mode = 'TESTNET' if self.config.TESTNET else '🔴 MAINNET (REAL MONEY!)'
        print(f"✅ Connected to Binance {mode}")
        
        # Fetch initial account data
        await self.update_account_info()
        
    async def update_account_info(self):
        """Get current account balance and positions"""
        try:
            account = await self.client.futures_account()
            
            # Get USDT balance
            for asset in account['assets']:
                if asset['asset'] == 'USDT':
                    self.account_balance = float(asset['walletBalance'])
                    break
            
            # Get open positions
            positions = await self.client.futures_position_information(symbol=self.config.SYMBOL)
            self.open_positions = [
                p for p in positions 
                if float(p['positionAmt']) != 0
            ]
            
            print(f"💰 Account Balance: ${self.account_balance:.2f} USDT")
            print(f"📊 Open Positions: {len(self.open_positions)}")
            
        except Exception as e:
            print(f"⚠️ Error fetching account info: {e}")
    
    async def stream_orderbook(self):
        """Stream order book updates"""
        socket = self.bsm.depth_socket(self.config.SYMBOL)
        
        async with socket as stream:
            while True:
                msg = await stream.recv()
                timestamp = datetime.now()
                
                # Update order book
                for bid in msg['b']:
                    price, qty = float(bid[0]), float(bid[1])
                    if qty == 0:
                        self.orderbook['bids'].pop(price, None)
                    else:
                        self.orderbook['bids'][price] = qty
                
                for ask in msg['a']:
                    price, qty = float(ask[0]), float(ask[1])
                    if qty == 0:
                        self.orderbook['asks'].pop(price, None)
                    else:
                        self.orderbook['asks'][price] = qty
                
                snapshot = {
                    'timestamp': timestamp,
                    'bids': dict(self.orderbook['bids']),
                    'asks': dict(self.orderbook['asks'])
                }
                self.orderbook_history.append(snapshot)
                
                for callback in self.orderbook_callbacks:
                    await callback(snapshot)
    
    async def stream_trades(self):
        """Stream executed trades"""
        socket = self.bsm.trade_socket(self.config.SYMBOL)
        
        async with socket as stream:
            while True:
                msg = await stream.recv()
                
                trade = {
                    'timestamp': datetime.fromtimestamp(msg['T'] / 1000),
                    'price': float(msg['p']),
                    'quantity': float(msg['q']),
                    'is_buyer_maker': msg['m'],
                    'trade_id': msg['t']
                }
                
                self.trades.append(trade)
                self.current_price = trade['price']
                
                for callback in self.trade_callbacks:
                    await callback(trade)
    
    async def stream_klines(self, interval: str):
        """Stream candlestick data for moving averages"""
        socket = self.bsm.kline_socket(self.config.SYMBOL, interval=interval)
        
        async with socket as stream:
            while True:
                msg = await stream.recv()
                kline = msg['k']
                
                candle = {
                    'timestamp': datetime.fromtimestamp(kline['t'] / 1000),
                    'open': float(kline['o']),
                    'high': float(kline['h']),
                    'low': float(kline['l']),
                    'close': float(kline['c']),
                    'volume': float(kline['v']),
                    'is_closed': kline['x']
                }
                
                if candle['is_closed']:
                    self.klines[interval].append(candle)
                    
                    for callback in self.kline_callbacks:
                        await callback(interval, candle)
    
    def get_closes(self, interval: str, periods: int) -> np.array:
        """Get closing prices for MA calculation"""
        if interval not in self.klines or len(self.klines[interval]) < periods:
            return np.array([])
        
        return np.array([k['close'] for k in list(self.klines[interval])[-periods:]])