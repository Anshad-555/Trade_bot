class EnhancedOrderFlowStrategy:
    """
    Complete trading strategy combining:
    - Order Flow (Spoofing, Absorption, Institutional)
    - Moving Averages (EMA crossovers)
    - Volume Profile (POC, Value Area)
    - Delta Divergence
    - Market Conditions
    """
    
    def __init__(self, config: BotConfig, 
                 heat_map, footprint, institutional,
                 indicators: TechnicalIndicators,
                 volume_profile: VolumeProfile,
                 delta_divergence: DeltaDivergenceDetector,
                 market_conditions: MarketConditionAnalyzer):
        
        self.config = config
        self.heat_map = heat_map
        self.footprint = footprint
        self.institutional = institutional
        self.indicators = indicators
        self.volume_profile = volume_profile
        self.delta_divergence = delta_divergence
        self.market_conditions = market_conditions
        
        self.last_signal = None
        
    async def analyze_market(self) -> dict:
        """
        Complete multi-timeframe, multi-indicator analysis
        """
        signal = {
            'timestamp': datetime.now(),
            'bias': 'neutral',
            'strength': 0,
            'reasons': [],
            'action': 'wait',
            'entry_price': 0,
            'stop_loss': 0,
            'take_profit': 0,
            'components': {}
        }
        
        # STEP 1: CHECK MARKET CONDITIONS
        conditions = await self.market_conditions.analyze_conditions()
        signal['components']['market_conditions'] = conditions
        
        if not conditions['is_tradeable']:
            signal['reasons'].append(f"⚠️ Market not tradeable: {', '.join(conditions['warnings'])}")
            return signal
        
        # STEP 2: MOVING AVERAGE ANALYSIS
        ma_signal = self._analyze_moving_averages()
        signal['components']['moving_averages'] = ma_signal
        
        if ma_signal['signal'] != 'none':
            signal['strength'] += ma_signal['strength']
            signal['reasons'].append(ma_signal['description'])
            if signal['bias'] == 'neutral':
                signal['bias'] = ma_signal['signal']
        
        # STEP 3: VOLUME PROFILE ANALYSIS
        vp_data = self.volume_profile.build_profile(lookback_hours=self.config.VP_LOOKBACK_HOURS)
        signal['components']['volume_profile'] = vp_data
        
        current_price = self.footprint.data_collector.current_price
        
        # Check if price is at key volume levels
        sr_levels = self.volume_profile.get_support_resistance()
        
        # Price at support = potential bounce
        if sr_levels['support'] and abs(current_price - sr_levels['support'][0]) / current_price < 0.005:
            signal['strength'] += 15
            signal['reasons'].append(f"📊 Price at major support: ${sr_levels['support'][0]:.2f}")
            if signal['bias'] == 'neutral':
                signal['bias'] = 'bullish'
        
        # Price at resistance = potential rejection
        if sr_levels['resistance'] and abs(current_price - sr_levels['resistance'][0]) / current_price < 0.005:
            signal['strength'] += 15
            signal['reasons'].append(f"📊 Price at major resistance: ${sr_levels['resistance'][0]:.2f}")
            if signal['bias'] == 'neutral':
                signal['bias'] = 'bearish'
        
        # STEP 4: DELTA DIVERGENCE
        divergence = self.delta_divergence.detect_divergence()
        signal['components']['delta_divergence'] = divergence
        
        if divergence['type'] != 'none':
            signal['strength'] += divergence['strength'] // 2  # Weight it less
            signal['reasons'].append(f"📈 {divergence['description']}")
            if signal['bias'] == 'neutral':
                signal['bias'] = divergence['type']
        
        # STEP 5: ORDER FLOW ANALYSIS (Original Logic)
        orderflow_signal = await self._analyze_orderflow()
        signal['components']['orderflow'] = orderflow_signal
        
        signal['strength'] += orderflow_signal['strength']
        signal['reasons'].extend(orderflow_signal['reasons'])
        
        if signal['bias'] == 'neutral' and orderflow_signal['bias'] != 'neutral':
            signal['bias'] = orderflow_signal['bias']
        
        # STEP 6: FINAL DECISION
        if signal['strength'] >= self.config.MIN_SIGNAL_STRENGTH:
            # Check if bias aligns with market conditions
            should_trade, reason = self.market_conditions.should_trade_in_current_conditions(signal['bias'])
            
            if should_trade:
                if signal['bias'] == 'bullish':
                    signal['action'] = 'buy'
                elif signal['bias'] == 'bearish':
                    signal['action'] = 'sell'
                
                # Calculate entry, stop, and target
                signal['entry_price'] = current_price
                
                if signal['action'] == 'buy':
                    signal['stop_loss'] = current_price * (1 - self.config.STOP_LOSS_PERCENT / 100)
                    signal['take_profit'] = current_price * (1 + self.config.TAKE_PROFIT_PERCENT / 100)
                else:
                    signal['stop_loss'] = current_price * (1 + self.config.STOP_LOSS_PERCENT / 100)
                    signal['take_profit'] = current_price * (1 - self.config.TAKE_PROFIT_PERCENT / 100)
            else:
                signal['reasons'].append(f"❌ {reason}")
        
        self.last_signal = signal
        return signal
    
    def _analyze_moving_averages(self) -> dict:
        """
        Analyze EMA crossovers and trends
        """
        result = {
            'signal': 'none',
            'strength': 0,
            'description': '',
            'emas': {}
        }
        
        # Get 5-minute closes for analysis
        closes = self.footprint.data_collector.get_closes('5m', 200)
        
        if len(closes) < 200:
            return result
        
        # Calculate all EMAs
        ema_fast = self.indicators.calculate_ema(closes[-self.config.EMA_FAST:], self.config.EMA_FAST)
        ema_medium = self.indicators.calculate_ema(closes[-self.config.EMA_MEDIUM:], self.config.EMA_MEDIUM)
        ema_slow = self.indicators.calculate_ema(closes[-self.config.EMA_SLOW:], self.config.EMA_SLOW)
        ema_trend = self.indicators.calculate_ema(closes[-self.config.EMA_TREND:], self.config.EMA_TREND)
        
        # Previous EMAs for crossover detection
        prev_fast = self.indicators.calculate_ema(closes[-(self.config.EMA_FAST+1):-1], self.config.EMA_FAST)
        prev_medium = self.indicators.calculate_ema(closes[-(self.config.EMA_MEDIUM+1):-1], self.config.EMA_MEDIUM)
        
        result['emas'] = {
            'fast': ema_fast,
            'medium': ema_medium,
            'slow': ema_slow,
            'trend': ema_trend
        }
        
        current_price = closes[-1]
        
        # Check for crossovers
        crossover = self.indicators.detect_ema_crossover(ema_fast, ema_medium, prev_fast, prev_medium)
        
        if crossover == 'bullish':
            result['strength'] = 25
            result['signal'] = 'bullish'
            result['description'] = f"🔄 Bullish EMA crossover: {self.config.EMA_FAST} crossed above {self.config.EMA_MEDIUM}"
            
            # Extra confirmation if above trend EMA
            if current_price > ema_trend:
                result['strength'] += 10
                result['description'] += " (above 200 EMA)"
        
        elif crossover == 'bearish':
            result['strength'] = 25
            result['signal'] = 'bearish'
            result['description'] = f"🔄 Bearish EMA crossover: {self.config.EMA_FAST} crossed below {self.config.EMA_MEDIUM}"
            
            if current_price < ema_trend:
                result['strength'] += 10
                result['description'] += " (below 200 EMA)"
        
        # Check EMA alignment (all in order = strong trend)
        if ema_fast > ema_medium > ema_slow > ema_trend:
            result['strength'] += 15
            result['signal'] = 'bullish'
            result['description'] = "📈 All EMAs aligned bullish"
        
        elif ema_fast < ema_medium < ema_slow < ema_trend:
            result['strength'] += 15
            result['signal'] = 'bearish'
            result['description'] = "📉 All EMAs aligned bearish"
        
        return result
    
    async def _analyze_orderflow(self) -> dict:
        """
        Original order flow analysis (from first version)
        """
        orderflow = {
            'bias': 'neutral',
            'strength': 0,
            'reasons': []
        }
        
        # Get order book
        orderbook = self.heat_map.data_collector.get_orderbook_snapshot()
        
        # Detect liquidity walls
        walls = self.heat_map.detect_liquidity_walls(orderbook)
        self.heat_map.track_wall_lifecycle(walls)
        
        if walls:
            orderflow['reasons'].append(f"🧱 Found {len(walls)} liquidity walls")
        
        # Check absorption
        footprint_df = self.footprint.build_footprint(timeframe_seconds=60)
        
        for wall in walls:
            absorption = self.footprint.detect_absorption(footprint_df, wall['price'], wall['side'])
            
            if absorption['detected']:
                orderflow['strength'] += 30
                orderflow['reasons'].append(f"💥 {absorption['message']}")
                orderflow['bias'] = absorption['direction']
        
        # Institutional activity
        large_trades = self.institutional.detect_large_trades(threshold_btc=10.0)
        if large_trades:
            recent = [t for t in large_trades if (datetime.now() - t['timestamp']).seconds < 120]
            
            if recent:
                buy_vol = sum(t['quantity'] for t in recent if t['side'] == 'buy')
                sell_vol = sum(t['quantity'] for t in recent if t['side'] == 'sell')
                
                if buy_vol > sell_vol * 2:
                    orderflow['strength'] += 20
                    orderflow['reasons'].append(f"🐋 Institutional buying: {buy_vol:.1f} BTC")
                    orderflow['bias'] = 'bullish'
                elif sell_vol > buy_vol * 2:
                    orderflow['strength'] += 20
                    orderflow['reasons'].append(f"🐋 Institutional selling: {sell_vol:.1f} BTC")
                    orderflow['bias'] = 'bearish'
        
        # Volume imbalance
        if not footprint_df.empty:
            total_buy = footprint_df['buy_volume'].sum()
            total_sell = footprint_df['sell_volume'].sum()
            imbalance = total_buy / (total_buy + total_sell)
            
            if imbalance > self.config.IMBALANCE_THRESHOLD:
                orderflow['strength'] += 20
                orderflow['reasons'].append(f"⚖️ Strong buy imbalance: {imbalance:.1%}")
                if orderflow['bias'] == 'neutral':
                    orderflow['bias'] = 'bullish'
            elif imbalance < (1 - self.config.IMBALANCE_THRESHOLD):
                orderflow['strength'] += 20
                orderflow['reasons'].append(f"⚖️ Strong sell imbalance: {(1-imbalance):.1%}")
                if orderflow['bias'] == 'neutral':
                    orderflow['bias'] = 'bearish'
        
        return orderflow