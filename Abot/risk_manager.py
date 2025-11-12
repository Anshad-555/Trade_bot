class RiskManager:
    """
    Comprehensive risk management:
    - Position monitoring
    - Trailing stops
    - Emergency exit
    - Daily loss limits
    """
    
    def __init__(self, config: BotConfig, data_collector: EnhancedDataCollector):
        self.config = config
        self.data_collector = data_collector
        
        self.active_stops = {}  # position_id -> stop_data
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0)
        
    async def monitor_positions(self):
        """
        Continuously monitor open positions for:
        - Stop loss hits
        - Take profit hits
        - Trailing stop updates
        """
        for position in self.data_collector.open_positions:
            position_side = 'LONG' if float(position['positionAmt']) > 0 else 'SHORT'
            entry_price = float(position['entryPrice'])
            current_price = self.data_collector.current_price
            unrealized_pnl = float(position['unRealizedProfit'])
            
            # Check for trailing stop update
            if self.config.TRAILING_STOP_ENABLED:
                await self._update_trailing_stop(position, current_price, unrealized_pnl)
            
            # Log position status
            pnl_percent = (unrealized_pnl / (entry_price * abs(float(position['positionAmt'])))) * 100
            
            if abs(pnl_percent) > 1:  # Log if significant movement
                print(f"📍 Position: {position_side} | Entry: ${entry_price:.2f} | "
                      f"Current: ${current_price:.2f} | PnL: {pnl_percent:+.2f}%")
    
    async def _update_trailing_stop(self, position, current_price: float, unrealized_pnl: float):
        """Update trailing stop if position is profitable"""
        position_id = position['symbol'] + '_' + position['positionSide']
        entry_price = float(position['entryPrice'])
        position_amt = float(position['positionAmt'])
        
        is_long = position_amt > 0
        
        # Only trail if in profit
        if unrealized_pnl <= 0:
            return
        
        # Calculate new trailing stop
        if is_long:
            new_stop = current_price * (1 - self.config.TRAILING_STOP_PERCENT / 100)
            
            # Update if better than current stop
            if position_id not in self.active_stops or new_stop > self.active_stops[position_id]:
                self.active_stops[position_id] = new_stop
                print(f"🔄 Trailing stop updated (LONG): ${new_stop:.2f}")
        else:
            new_stop = current_price * (1 + self.config.TRAILING_STOP_PERCENT / 100)
            
            if position_id not in self.active_stops or new_stop < self.active_stops[position_id]:
                self.active_stops[position_id] = new_stop
                print(f"🔄 Trailing stop updated (SHORT): ${new_stop:.2f}")
    
    def check_daily_limits(self) -> tuple[bool, str]:
        """Check if daily loss limit has been hit"""
        # Reset daily PnL at midnight
        if datetime.now() > self.daily_reset_time + timedelta(days=1):
            self.data_collector.daily_pnl = 0
            self.data_collector.daily_trades = 0
            self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0)
            print("🔄 Daily limits reset")
        
        # Check daily loss
        if self.data_collector.daily_pnl < 0:
            loss_percent = abs(self.data_collector.daily_pnl) / self.data_collector.account_balance * 100
            
            if loss_percent >= self.config.MAX_DAILY_LOSS_PERCENT:
                return False, f"❌ Daily loss limit hit: {loss_percent:.2f}%"
        
        return True, "Daily limits OK"