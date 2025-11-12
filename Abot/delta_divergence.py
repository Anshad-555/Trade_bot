class DeltaDivergenceDetector:
    """
    Detects divergences between price and cumulative delta:
    - Bullish Divergence: Price down, Delta up (hidden buying)
    - Bearish Divergence: Price up, Delta down (hidden selling)
    """
    
    def __init__(self, config: BotConfig, footprint_analyzer):
        self.config = config
        self.footprint = footprint_analyzer
        
        # Historical deltas
        self.delta_history = deque(maxlen=100)
        
    def calculate_cumulative_delta(self, timeframe_minutes: int = 5) -> float:
        """
        Calculate cumulative delta (buy volume - sell volume)
        """
        footprint_df = self.footprint.build_footprint(timeframe_seconds=timeframe_minutes * 60)
        
        if footprint_df.empty:
            return 0.0
        
        cumulative_delta = footprint_df['delta'].sum()
        
        # Store for history
        self.delta_history.append({
            'timestamp': datetime.now(),
            'delta': cumulative_delta,
            'price': self.footprint.data_collector.current_price
        })
        
        return cumulative_delta
    
    def detect_divergence(self) -> dict:
        """
        Detect divergences between price and delta
        
        Returns: {
            'type': 'bullish', 'bearish', or 'none',
            'strength': 0-100,
            'description': str
        }
        """
        if len(self.delta_history) < self.config.DELTA_DIVERGENCE_PERIODS:
            return {'type': 'none', 'strength': 0}
        
        recent_data = list(self.delta_history)[-self.config.DELTA_DIVERGENCE_PERIODS:]
        
        # Calculate price trend
        prices = [d['price'] for d in recent_data]
        price_change = (prices[-1] - prices[0]) / prices[0]
        
        # Calculate delta trend
        deltas = [d['delta'] for d in recent_data]
        delta_change = (deltas[-1] - deltas[0]) / (abs(deltas[0]) + 1)  # Avoid div by zero
        
        # Detect divergence
        divergence_strength = abs(price_change - delta_change)
        
        # Bullish Divergence: Price falling, Delta rising
        if price_change < -0.01 and delta_change > 0.01 and divergence_strength > self.config.DELTA_DIVERGENCE_THRESHOLD:
            return {
                'type': 'bullish',
                'strength': min(100, int(divergence_strength * 200)),
                'description': f'Bullish divergence: Price down {price_change:.1%}, Delta up {delta_change:.1%}'
            }
        
        # Bearish Divergence: Price rising, Delta falling
        if price_change > 0.01 and delta_change < -0.01 and divergence_strength > self.config.DELTA_DIVERGENCE_THRESHOLD:
            return {
                'type': 'bearish',
                'strength': min(100, int(divergence_strength * 200)),
                'description': f'Bearish divergence: Price up {price_change:.1%}, Delta down {delta_change:.1%}'
            }
        
        return {'type': 'none', 'strength': 0}