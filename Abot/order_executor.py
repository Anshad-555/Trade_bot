from binance.exceptions import BinanceAPIException

class OrderExecutor:
    """
    Production-grade order execution with:
    - Market orders
    - Stop loss / Take profit
    - Error handling
    - Order tracking
    """
    
    def __init__(self, config: BotConfig, data_collector: EnhancedDataCollector,
                 position_sizer: PositionSizer, risk_manager: RiskManager):
        self.config = config
        self.data_collector = data_collector
        self.position_sizer = position_sizer
        self.risk_manager = risk_manager
        
        self.orders = {}  # Track all orders
        
    async def execute_signal(self, signal: dict):
        """
        Execute trading signal with full risk management
        """
        if not self.config.ENABLE_TRADING:
            print("⚠️ Trading disabled in config")
            return
        
        if self.config.EMERGENCY_STOP:
            print("🚨 EMERGENCY STOP ACTIVE - No new trades")
            return
        
        # Check daily limits
        can_trade, reason = self.risk_manager.check_daily_limits()
        if not can_trade:
            print(reason)
            return
        
        # Calculate position size
        position_size = self.position_sizer.calculate_position_size(
            entry_price=signal['entry_price'],
            stop_loss_price=signal['stop_loss'],
            signal_strength=signal['strength']
        )
        
        # Validate position size
        is_valid, validation_msg = self.position_sizer.check_risk_limits(position_size)
        if not is_valid:
            print(f"❌ Position rejected: {validation_msg}")
            return
        
        # Execute the trade
        await self._place_market_order(signal, position_size)
    
    async def _place_market_order(self, signal: dict, position_size: dict):
        """
        Place market order with stop loss and take profit
        """
        side = 'BUY' if signal['action'] == 'buy' else 'SELL'
        
        print(f"\n{'='*80}")
        print(f"🎯 EXECUTING TRADE - {self.config.SYMBOL}")
        print(f"{'='*80}")
        print(f"Direction: {side}")
        print(f"Entry Price: ${signal['entry_price']:.2f}")
        print(f"Position Size: {position_size['quantity_btc']:.6f} BTC (${position_size['notional_usdt']:.2f})")
        print(f"Risk Amount: ${position_size['risk_usdt']:.2f} ({position_size.get('risk_percent', 0):.2f}%)")
        print(f"Stop Loss: ${signal['stop_loss']:.2f} ({self.config.STOP_LOSS_PERCENT}%)")
        print(f"Take Profit: ${signal['take_profit']:.2f} ({self.config.TAKE_PROFIT_PERCENT}%)")
        print(f"Leverage: {self.config.LEVERAGE}x")
        print(f"Signal Strength: {signal['strength']}/100")
        print(f"\nReasons:")
        for reason in signal['reasons']:
            print(f"  • {reason}")
        print(f"{'='*80}\n")
        
        try:
            # Set leverage
            await self.data_collector.client.futures_change_leverage(
                symbol=self.config.SYMBOL,
                leverage=self.config.LEVERAGE
            )
            
            # Place market order
            order = await self.data_collector.client.futures_create_order(
                symbol=self.config.SYMBOL,
                side=side,
                type='MARKET',
                quantity=round(position_size['quantity_btc'], 6)
            )
            
            print(f"✅ Market order filled: {order['orderId']}")
            print(f"   Filled Qty: {order['executedQty']} BTC")
            print(f"   Avg Price: ${float(order['avgPrice']):.2f}")
            
            # Place stop loss
            sl_side = 'SELL' if side == 'BUY' else 'BUY'
            sl_order = await self.data_collector.client.futures_create_order(
                symbol=self.config.SYMBOL,
                side=sl_side,
                type='STOP_MARKET',
                stopPrice=round(signal['stop_loss'], 2),
                quantity=round(position_size['quantity_btc'], 6),
                reduceOnly=True
            )
            
            print(f"✅ Stop Loss placed: {sl_order['orderId']} @ ${signal['stop_loss']:.2f}")
            
            # Place take profit
            tp_order = await self.data_collector.client.futures_create_order(
                symbol=self.config.SYMBOL,
                side=sl_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=round(signal['take_profit'], 2),
                quantity=round(position_size['quantity_btc'], 6),
                reduceOnly=True
            )
            
            print(f"✅ Take Profit placed: {tp_order['orderId']} @ ${signal['take_profit']:.2f}")
            
            # Store order data
            self.orders[order['orderId']] = {
                'entry_order': order,
                'stop_loss': sl_order,
                'take_profit': tp_order,
                'signal': signal,
                'position_size': position_size,
                'timestamp': datetime.now()
            }
            
            # Update account info
            await self.data_collector.update_account_info()
            
            print(f"\n🎉 Trade executed successfully!\n")
            
        except BinanceAPIException as e:
            print(f"❌ Binance API Error: {e.message}")
            print(f"   Error Code: {e.code}")
        except Exception as e:
            print(f"❌ Execution error: {e}")