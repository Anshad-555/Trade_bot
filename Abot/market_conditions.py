class MarketConditionAnalyzer:
    """
    Detect market conditions:
    - Trending vs Ranging
    - High vs Low Volatility
    - Liquidity conditions
    - Spread analysis
    """
    
    def __init__(self, config: BotConfig, data_collector: EnhancedDataCollector,
                 technical_indicators: TechnicalIndicators):
        self.config = config
        self.data_collector = data_collector
        self.indicators = technical_indicators
        
        self.current_regime = 'unknown'  # 'trending_up', 'trending_down', 'ranging'
        self.volatility_state = 'normal'  # 'low', 'normal', 'high', 'extreme'
        self.liquidity_state = 'good'  # 'good', 'poor'
        
    async def analyze_conditions(self) -> dict:
        """
        Complete market condition analysis
        
        Returns: {
            'regime': str,
            'volatility': str,
            'spread': float,
            'volume_24h': float,
            'is_tradeable': bool,
            'warnings': list
        }
        """
        conditions = {
            'regime': 'unknown',
            'volatility': 'normal',
            'spread_bips': 0,
            'volume_24h': 0,
            'is_tradeable': True,
            'warnings': []
        }
        
        # 1. DETECT MARKET REGIME (Trending vs Ranging)
        regime = await self._detect_regime()
        conditions['regime'] = regime
        self.current_regime = regime
        
        # 2. MEASURE VOLATILITY
        volatility = self._measure_volatility()
        conditions['volatility'] = volatility
        self.volatility_state = volatility
        
        # 3. CHECK SPREAD
        spread = self._calculate_spread()
        conditions['spread_bips'] = spread
        
        if spread > self.config.MAX_SPREAD_BIPS:
            conditions['is_tradeable'] = False
            conditions['warnings'].append(f"Spread too wide: {spread:.1f} bips")
        
        # 4. CHECK 24H VOLUME
        volume_24h = await self._get_24h_volume()
        conditions['volume_24h'] = volume_24h
        
        if volume_24h < self.config.MIN_VOLUME_24H_USDT:
            conditions['is_tradeable'] = False
            conditions['warnings'].append(f"Low 24h volume: ${volume_24h/1e9:.2f}B")
        
        # 5. VOLATILITY CHECK
        if volatility == 'extreme':
            conditions['warnings'].append("Extreme volatility detected - use caution")
        elif volatility == 'low':
            conditions['warnings'].append("Low volatility - reduce position sizes")
        
        return conditions
    
    async def _detect_regime(self) -> str:
        """
        Detect if market is trending or ranging
        Uses EMA slopes and price action
        """
        # Get 15-minute closes
        closes = self.data_collector.get_closes('15m', 50)
        
        if len(closes) < 50:
            return 'unknown'
        
        # Calculate EMAs
        ema_20 = self.indicators.calculate_ema(closes[-20:], 20)
        ema_50 = self.indicators.calculate_ema(closes[-50:], 50)
        
        # Calculate price change over period
        price_change = (closes[-1] - closes[0]) / closes[0]
        
        # Trending conditions
        if price_change > self.config.TREND_THRESHOLD and ema_20 > ema_50:
            return 'trending_up'
        elif price_change < -self.config.TREND_THRESHOLD and ema_20 < ema_50:
            return 'trending_down'
        
        # Ranging conditions
        if abs(price_change) < self.config.RANGING_THRESHOLD:
            return 'ranging'
        
        return 'transitioning'
    
    def _measure_volatility(self) -> str:
        """
        Measure current volatility state
        """
        closes = self.data_collector.get_closes('1m', 60)
        
        if len(closes) < 60:
            return 'normal'
        
        volatility = self.indicators.calculate_volatility(closes, periods=60)
        
        if volatility < self.config.MIN_VOLATILITY_PERCENT:
            return 'low'
        elif volatility > self.config.MAX_VOLATILITY_PERCENT:
            return 'extreme'
        elif volatility > self.config.MAX_VOLATILITY_PERCENT * 0.7:
            return 'high'
        
        return 'normal'
    
    def _calculate_spread(self) -> float:
        """
        Calculate bid-ask spread in basis points
        """
        orderbook = self.data_collector.orderbook
        
        if not orderbook['bids'] or not orderbook['asks']:
            return 1000  # Very high spread if no data
        
        best_bid = max(orderbook['bids'].keys())
        best_ask = min(orderbook['asks'].keys())
        
        spread = (best_ask - best_bid) / best_bid * 10000  # Basis points
        
        return spread
    
    async def _get_24h_volume(self) -> float:
        """Get 24-hour trading volume"""
        try:
            ticker = await self.data_collector.client.futures_ticker(symbol=self.config.SYMBOL)
            return float(ticker['quoteVolume'])
        except:
            return 0.0
    
    def should_trade_in_current_conditions(self, signal_bias: str) -> tuple[bool, str]:
        """
        Determine if trading is appropriate given current market conditions
        
        Args:
            signal_bias: 'bullish' or 'bearish'
        
        Returns: (should_trade, reason)
        """
        # Don't trade in ranging markets with directional signals
        if self.current_regime == 'ranging':
            return False, "Market is ranging - avoid directional trades"
        
        # Check if bias aligns with trend
        if self.config.REQUIRE_TREND_CONFIRMATION:
            if signal_bias == 'bullish' and self.current_regime == 'trending_down':
                return False, "Bullish signal against downtrend"
            if signal_bias == 'bearish' and self.current_regime == 'trending_up':
                return False, "Bearish signal against uptrend"
        
        # Extreme volatility warning
        if self.volatility_state == 'extreme':
            return False, "Volatility too high - risk of whipsaw"
        
        return True, "Market conditions favorable"