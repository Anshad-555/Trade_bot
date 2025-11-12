class PositionSizer:
    """
    Advanced position sizing strategies:
    - Fixed Percent Risk
    - Fixed Dollar Amount
    - Kelly Criterion
    - Volatility-adjusted sizing
    """
    
    def __init__(self, config: BotConfig, data_collector: EnhancedDataCollector):
        self.config = config
        self.data_collector = data_collector
        
    def calculate_position_size(self, entry_price: float, stop_loss_price: float, 
                               signal_strength: int = 50) -> dict:
        """
        Calculate optimal position size based on configured method
        
        Returns: {
            'quantity_btc': float,
            'notional_usdt': float,
            'risk_usdt': float,
            'method': str
        }
        """
        account_balance = self.data_collector.account_balance
        
        if account_balance <= 0:
            return {'quantity_btc': 0, 'notional_usdt': 0, 'risk_usdt': 0, 'method': 'no_balance'}
        
        # Calculate risk per unit
        risk_per_btc = abs(entry_price - stop_loss_price)
        risk_percent = risk_per_btc / entry_price
        
        if self.config.POSITION_SIZING_METHOD == 'fixed_percent':
            return self._fixed_percent_sizing(account_balance, entry_price, risk_per_btc)
        
        elif self.config.POSITION_SIZING_METHOD == 'fixed_dollar':
            return self._fixed_dollar_sizing(entry_price, risk_per_btc)
        
        elif self.config.POSITION_SIZING_METHOD == 'kelly':
            return self._kelly_sizing(account_balance, entry_price, risk_per_btc, signal_strength)
        
        else:
            # Default to fixed percent
            return self._fixed_percent_sizing(account_balance, entry_price, risk_per_btc)
    
    def _fixed_percent_sizing(self, balance: float, entry_price: float, risk_per_btc: float) -> dict:
        """
        Risk X% of account balance per trade
        Example: $1000 balance, 1% risk = $10 risk
        """
        risk_amount = balance * (self.config.RISK_PER_TRADE_PERCENT / 100)
        quantity_btc = risk_amount / risk_per_btc
        notional_usdt = quantity_btc * entry_price
        
        return {
            'quantity_btc': quantity_btc,
            'notional_usdt': notional_usdt,
            'risk_usdt': risk_amount,
            'method': 'fixed_percent',
            'risk_percent': self.config.RISK_PER_TRADE_PERCENT
        }
    
    def _fixed_dollar_sizing(self, entry_price: float, risk_per_btc: float) -> dict:
        """
        Trade fixed dollar amount per position
        Example: Always trade $50 worth of BTC
        """
        notional_usdt = self.config.FIXED_POSITION_SIZE_USDT
        quantity_btc = notional_usdt / entry_price
        risk_amount = quantity_btc * risk_per_btc
        
        return {
            'quantity_btc': quantity_btc,
            'notional_usdt': notional_usdt,
            'risk_usdt': risk_amount,
            'method': 'fixed_dollar'
        }
    
    def _kelly_sizing(self, balance: float, entry_price: float, 
                     risk_per_btc: float, signal_strength: int) -> dict:
        """
        Kelly Criterion: f* = (bp - q) / b
        where:
        - b = risk/reward ratio
        - p = win probability
        - q = loss probability (1-p)
        
        Adjusted by signal strength
        """
        # Kelly formula
        win_rate = self.config.KELLY_WIN_RATE
        risk_reward = self.config.KELLY_RISK_REWARD
        
        kelly_percent = ((win_rate * risk_reward) - (1 - win_rate)) / risk_reward
        kelly_percent = max(0, kelly_percent)  # No negative sizing
        
        # Apply Kelly fraction for safety
        kelly_percent *= self.config.KELLY_FRACTION
        
        # Adjust by signal strength (50-100% confidence)
        confidence_factor = signal_strength / 100
        kelly_percent *= confidence_factor
        
        # Calculate position
        risk_amount = balance * kelly_percent
        quantity_btc = risk_amount / risk_per_btc
        notional_usdt = quantity_btc * entry_price
        
        return {
            'quantity_btc': quantity_btc,
            'notional_usdt': notional_usdt,
            'risk_usdt': risk_amount,
            'method': 'kelly',
            'kelly_percent': kelly_percent * 100
        }
    
    def check_risk_limits(self, position_size: dict) -> tuple[bool, str]:
        """
        Verify position doesn't exceed risk limits
        
        Returns: (is_valid, reason)
        """
        balance = self.data_collector.account_balance
        
        # Check maximum account risk
        max_risk = balance * (self.config.MAX_ACCOUNT_RISK_PERCENT / 100)
        if position_size['risk_usdt'] > max_risk:
            return False, f"Position risk ${position_size['risk_usdt']:.2f} exceeds max ${max_risk:.2f}"
        
        # Check daily loss limit
        if self.data_collector.daily_pnl < 0:
            daily_loss_percent = abs(self.data_collector.daily_pnl) / balance * 100
            if daily_loss_percent >= self.config.MAX_DAILY_LOSS_PERCENT:
                return False, f"Daily loss limit reached: {daily_loss_percent:.1f}%"
        
        # Check maximum positions
        if len(self.data_collector.open_positions) >= self.config.MAX_POSITIONS:
            return False, f"Maximum positions reached: {self.config.MAX_POSITIONS}"
        
        return True, "Position size valid"