class TechnicalIndicators:
    """
    Calculate technical indicators:
    - EMAs (Fast, Medium, Slow, Trend)
    - Volume-weighted averages
    - Volatility metrics
    """
    
    @staticmethod
    def calculate_ema(prices: np.array, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return 0.0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    @staticmethod
    def calculate_ema_series(prices: np.array, period: int) -> np.array:
        """Calculate EMA for entire series"""
        if len(prices) < period:
            return np.array([])
        
        emas = np.zeros(len(prices))
        emas[0] = prices[0]
        multiplier = 2 / (period + 1)
        
        for i in range(1, len(prices)):
            emas[i] = (prices[i] * multiplier) + (emas[i-1] * (1 - multiplier))
        
        return emas
    
    @staticmethod
    def detect_ema_crossover(fast_ema: float, slow_ema: float, 
                            prev_fast: float, prev_slow: float) -> str:
        """
        Detect EMA crossovers
        Returns: 'bullish', 'bearish', or 'none'
        """
        # Bullish crossover: fast crosses above slow
        if prev_fast <= prev_slow and fast_ema > slow_ema:
            return 'bullish'
        
        # Bearish crossover: fast crosses below slow
        if prev_fast >= prev_slow and fast_ema < slow_ema:
            return 'bearish'
        
        return 'none'
    
    @staticmethod
    def calculate_volatility(prices: np.array, periods: int = 14) -> float:
        """Calculate price volatility (standard deviation)"""
        if len(prices) < periods:
            return 0.0
        
        returns = np.diff(prices[-periods:]) / prices[-periods:-1]
        return np.std(returns) * 100  # As percentage
    
    @staticmethod
    def calculate_atr(highs: np.array, lows: np.array, closes: np.array, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(highs) < period or len(lows) < period or len(closes) < period:
            return 0.0
        
        tr_list = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
        
        return np.mean(tr_list[-period:])