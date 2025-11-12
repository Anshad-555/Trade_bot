import logging
import signal as sys_signal

class ProductionOrderFlowBot:
    """
    Production-ready bot with all features integrated
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.setup_logging()
        
        # Core modules
        self.data_collector = None
        self.indicators = None
        self.heat_map = None
        self.footprint = None
        self.institutional = None
        self.volume_profile = None
        self.delta_divergence = None
        self.market_conditions = None
        self.strategy = None
        self.position_sizer = None
        self.risk_manager = None
        self.order_executor = None
        
        self.is_running = False
        
        # Setup graceful shutdown
        sys_signal.signal(sys_signal.SIGINT, self._signal_handler)
        sys_signal.signal(sys_signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n🛑 Shutdown signal received...")
        self.is_running = False
    
    def setup_logging(self):
        """Configure production logging"""
g.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ProductionBot')
    
    async def initialize(self):
        """Initialize all components"""
        print("\n" + "="*80)
        print("🚀 INITIALIZING PRODUCTION ORDER FLOW BOT")
        print("="*80)
        
        # Warn if using real money
        if not self.config.TESTNET:
            print("\n⚠️  WARNING: MAINNET MODE - TRADING WITH REAL MONEY!")
            print("⚠️  Make sure you understand all risks before proceeding!")
            print("\nPress Ctrl+C within 10 seconds to cancel...\n")
            await asyncio.sleep(10)
        
        self.logger.info("Initializing data collector...")
        self.data_collector = EnhancedDataCollector(self.config)
        await self.data_collector.connect()
        
        self.logger.info("Initializing technical indicators...")
        self.indicators = TechnicalIndicators()
        
        self.logger.info("Initializing order flow analyzers...")
        from heat_map_analyzer import HeatMapAnalyzer
        from footprint_analyzer import FootprintAnalyzer
        from institutional_detector import InstitutionalDetector
        
        self.heat_map = HeatMapAnalyzer(self.config, self.data_collector)
        self.footprint = FootprintAnalyzer(self.config, self.data_collector)
        self.institutional = InstitutionalDetector(self.config, self.data_collector)
        
        self.logger.info("Initializing advanced analyzers...")
        self.volume_profile = VolumeProfile(self.config, self.data_collector)
        self.delta_divergence = DeltaDivergenceDetector(self.config, self.footprint)
        self.market_conditions = MarketConditionAnalyzer(self.config, self.data_collector, self.indicators)
        
        self.logger.info("Initializing strategy...")
        self.strategy = EnhancedOrderFlowStrategy(
            self.config,
            self.heat_map,
            self.footprint,
            self.institutional,
            self.indicators,
            self.volume_profile,
            self.delta_divergence,
            self.market_conditions
        )
        
        self.logger.info("Initializing risk management...")
        self.position_sizer = PositionSizer(self.config, self.data_collector)
        self.risk_manager = RiskManager(self.config, self.data_collector)
        
        self.logger.info("Initializing order executor...")
        self.order_executor = OrderExecutor(
            self.config,
            self.data_collector,
            self.position_sizer,
            self.risk_manager
        )
        
        print("\n✅ All modules initialized successfully!")
        print(f"📊 Trading Pair: {self.config.SYMBOL}")
        print(f"💰 Account Balance: ${self.data_collector.account_balance:.2f} USDT")
        print(f"⚙️  Leverage: {self.config.LEVERAGE}x")
        print(f"🎯 Risk Per Trade: {self.config.RISK_PER_TRADE_PERCENT}%")
        print(f"🛡️  Stop Loss: {self.config.STOP_LOSS_PERCENT}%")
        print(f"🎁 Take Profit: {self.config.TAKE_PROFIT_PERCENT}%")
        print("="*80 + "\n")
    
    async def run(self):
        """Main bot loop"""
        self.is_running = True
        
        # Start all data streams
        self.logger.info("Starting data streams...")
        asyncio.create_task(self.data_collector.stream_orderbook())
        asyncio.create_task(self.data_collector.stream_trades())
        
        for interval in self.config.KLINE_INTERVALS:
            asyncio.create_task(self.data_collector.stream_klines(interval))
        
        # Wait for initial data to populate
        self.logger.info("Waiting for initial data (30 seconds)...")
        await asyncio.sleep(30)
        
        self.logger.info("🟢 Bot is now live and analyzing markets...")
        
        analysis_counter = 0
        
        while self.is_running:
            try:
                # Check emergency stop
                if self.config.EMERGENCY_STOP:
                    self.logger.warning("🚨 EMERGENCY STOP ACTIVATED")
                    break
                
                # Analyze market every 5 seconds
                if analysis_counter % 5 == 0:
                    signal = await self.strategy.analyze_market()
                    
                    # Log current state
                    self.logger.info(
                        f"Market: {signal['bias'].upper()} | "
                        f"Strength: {signal['strength']}/100 | "
                        f"Action: {signal['action'].upper()}"
                    )
                    
                    # Execute if signal is strong enough
                    if signal['action'] in ['buy', 'sell']:
                        await self.order_executor.execute_signal(signal)
                
                # Monitor positions every second
                await self.risk_manager.monitor_positions()
                
                # Update account info every 60 seconds
                if analysis_counter % 60 == 0:
                    await self.data_collector.update_account_info()
                
                analysis_counter += 1
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("🛑 Initiating graceful shutdown...")
        self.is_running = False
        
        # Close all positions if emergency
        if self.config.EMERGENCY_STOP:
            self.logger.warning("⚠️ Emergency stop - consider closing positions manually")
        
        # Close connection
        if self.data_collector and self.data_collector.client:
            await self.data_collector.client.close_connection()
        
        self.logger.info("✅ Shutdown complete")
        print("\n" + "="*80)
        print("Bot stopped. Stay safe and trade responsibly!")
        print("="*80 + "\n")