import logging

logger = logging.getLogger(__name__)

class PortfolioManager:
    def __init__(self, event_bus, portfolio_config):
        self.event_bus = event_bus
        self.config = portfolio_config # يحتوي على العملات ونسبها
        self.holdings = {} # رصيدك الفعلي
        
        # الاشتراك في إشارات التداول للتنفيذ
        self.event_bus.subscribe("trade_signal", self.execute_dca)

    def execute_dca(self, data):
        """تنفيذ الشراء بناءً على إشارة الاستراتيجية وخطتك للتجميع"""
        symbol = data.get("symbol")
        score = data.get("score")
        
        # الذكاء هنا: إذا كان الـ Score مرتفعاً جداً، نزيد كمية الـ DCA
        # إذا كان Score متوسطاً، نشتري الحد الأدنى
        dca_multiplier = 1.0 if score > 0.8 else 0.5
        
        logger.info(f"💰 PortfolioManager: DCA triggered for {symbol}. Multiplier: {dca_multiplier}")
        
        # إرسال أمر شراء سبوت
        self.event_bus.publish("execution_request", {
            "symbol": symbol,
            "action": "BUY",
            "quantity": self.calculate_amount(symbol) * dca_multiplier,
            "type": "SPOT"
        })

    def calculate_amount(self, symbol):
        """حساب الكمية بناءً على النسبة المئوية المحددة للعملة"""
        target_allocation = self.config.get(symbol, 0.1) # مثلاً 10% من المحفظة
        # منطق حساب الكمية بناءً على رصيد الكاش المتاح
        return 100 # كمية افتراضية للتجربة