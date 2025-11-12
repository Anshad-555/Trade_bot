class VolumeProfile:
    """
    Volume Profile Analysis:
    - Point of Control (POC) - highest volume price
    - Value Area (VA) - 70% of volume concentration
    - High/Low Volume Nodes
    """
    
    def __init__(self, config: BotConfig, data_collector: EnhancedDataCollector):
        self.config = config
        self.data_collector = data_collector
        
        # Volume profile data
        self.profile = {}  # price -> volume
        self.poc = 0.0  # Point of Control
        self.value_area_high = 0.0
        self.value_area_low = 0.0
        
    def build_profile(self, lookback_hours: int = 24) -> dict:
        """
        Build volume profile from recent trades
        """
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        
        # Filter recent trades
        recent_trades = [
            t for t in self.data_collector.trades
            if t['timestamp'] > cutoff_time
        ]
        
        if not recent_trades:
            return {}
        
        # Get price range
        prices = [t['price'] for t in recent_trades]
        min_price = min(prices)
        max_price = max(prices)
        
        # Create price bins
        bin_size = (max_price - min_price) / self.config.VP_PRICE_BINS
        
        # Aggregate volume by price bin
        volume_by_price = {}
        
        for trade in recent_trades:
            # Assign to bin
            bin_index = int((trade['price'] - min_price) / bin_size)
            bin_price = min_price + (bin_index * bin_size)
            
            if bin_price not in volume_by_price:
                volume_by_price[bin_price] = 0
            
            volume_by_price[bin_price] += trade['quantity']
        
        self.profile = volume_by_price
        
        # Calculate POC (Point of Control)
        if volume_by_price:
            self.poc = max(volume_by_price, key=volume_by_price.get)
        
        # Calculate Value Area (70% of volume)
        self._calculate_value_area()
        
        return {
            'profile': self.profile,
            'poc': self.poc,
            'value_area_high': self.value_area_high,
            'value_area_low': self.value_area_low,
            'total_volume': sum(volume_by_price.values())
        }
    
    def _calculate_value_area(self):
        """Calculate Value Area (70% volume concentration)"""
        if not self.profile:
            return
        
        total_volume = sum(self.profile.values())
        target_volume = total_volume * (self.config.VP_VALUE_AREA_PERCENT / 100)
        
        # Start from POC and expand outward
        sorted_prices = sorted(self.profile.keys())
        poc_index = sorted_prices.index(self.poc)
        
        va_volume = self.profile[self.poc]
        low_index = poc_index
        high_index = poc_index
        
        while va_volume < target_volume:
            # Check which direction has more volume
            low_vol = self.profile[sorted_prices[low_index - 1]] if low_index > 0 else 0
            high_vol = self.profile[sorted_prices[high_index + 1]] if high_index < len(sorted_prices) - 1 else 0
            
            if low_vol > high_vol and low_index > 0:
                low_index -= 1
                va_volume += low_vol
            elif high_index < len(sorted_prices) - 1:
                high_index += 1
                va_volume += high_vol
            else:
                break
        
        self.value_area_low = sorted_prices[low_index]
        self.value_area_high = sorted_prices[high_index]
    
    def is_price_in_value_area(self, price: float) -> bool:
        """Check if price is within value area"""
        return self.value_area_low <= price <= self.value_area_high
    
    def get_support_resistance(self) -> dict:
        """Identify high volume nodes as support/resistance"""
        if not self.profile:
            return {'support': [], 'resistance': []}
        
        current_price = self.data_collector.current_price
        
        # Find high volume nodes
        avg_volume = sum(self.profile.values()) / len(self.profile)
        threshold = avg_volume * 1.5  # 1.5x average = significant node
        
        significant_nodes = [
            price for price, volume in self.profile.items()
            if volume >= threshold
        ]
        
        support = [p for p in significant_nodes if p < current_price]
        resistance = [p for p in significant_nodes if p > current_price]
        
        return {
            'support': sorted(support, reverse=True)[:3],  # Top 3 closest
            'resistance': sorted(resistance)[:3]
        }