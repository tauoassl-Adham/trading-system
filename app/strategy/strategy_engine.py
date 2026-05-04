import logging

logger = logging.getLogger(__name__)


class ScoreCalculator:
    def calculate_core_score(self, core_data):
        structure = core_data.get("structure_score", 0)
        zone = core_data.get("zone_score", 0)
        reaction = core_data.get("reaction_score", 0)
        return (structure + zone + reaction) / 3

    def calculate_confirmer_score(self, confirmers):
        macro = confirmers.get("macro", 0)
        momentum = confirmers.get("momentum", 0)
        return (macro + momentum) / 2

    def calculate_final_score(self, core, conf):
        return (core * 0.6) + (conf * 0.4)


class RiskManager:
    def calculate_levels(self, action, entry, ob):
        if not ob:
            return None, None

        if action == "BUY":
            sl = ob.get("low")
            tp = entry + (abs(entry - sl) * 2)
        else:
            sl = ob.get("high")
            tp = entry - (abs(entry - sl) * 2)

        return sl, tp


class StrategyEngine:
    def __init__(self, event_bus):
        self.event_bus = event_bus

        self.scorer = ScoreCalculator()
        self.risk = RiskManager()

        self.market_bias = "NEUTRAL"
        self.last_confirmers = {}

        self.MIN_CONFIDENCE = 0.6

        # subscriptions
        self.event_bus.subscribe("candle_closed_1d", self.update_bias)
        self.event_bus.subscribe("candle_closed_15m", self.process_signal)
        self.event_bus.subscribe("analytics_update", self.receive_confirmers)
        self.event_bus.subscribe("tick", self.process_tick)

        logger.info("StrategyEngine READY")

    # -------------------------
    # BIAS
    # -------------------------
    def update_bias(self, data):
        candle = data.get("candle")
        if not candle:
            return

        if candle["close"] > candle["open"]:
            self.market_bias = "BUY"
        elif candle["close"] < candle["open"]:
            self.market_bias = "SELL"
        else:
            self.market_bias = "NEUTRAL"

        logger.info(f"BIAS UPDATED: {self.market_bias}")

    # -------------------------
    # CONFIRMERS
    # -------------------------
    def receive_confirmers(self, data):
        logger.info(f"CONFIRMERS RECEIVED RAW: {data}")

        self.last_confirmers = data.get("confirmers", {
            "macro": 0.8,
            "momentum": 0.8
        })

        logger.info(f"LAST CONFIRMERS STATE: {self.last_confirmers}")

    # -------------------------
    # CORE SIGNAL
    # -------------------------
    def process_signal(self, data):
        core = data.get("core", {})
        if not core:
            return

        # bias filter
        if self.market_bias != "NEUTRAL" and core.get("bias") != self.market_bias:
            logger.info("FILTERED (bias mismatch)")
            return

        core_score = self.scorer.calculate_core_score(core)

        conf_score = self.scorer.calculate_confirmer_score(
            self.last_confirmers or {"macro": 0.8, "momentum": 0.8}
        )

        final = self.scorer.calculate_final_score(core_score, conf_score)

        logger.info(f"SCORES → core:{core_score:.2f} conf:{conf_score:.2f} final:{final:.2f}")

        if final < self.MIN_CONFIDENCE:
            logger.info("REJECTED (low confidence)")
            return

        action = core.get("bias")
        entry = core.get("entry_price")
        ob = core.get("order_block")

        sl, tp = self.risk.calculate_levels(action, entry, ob)
        if not sl:
            return

        self.event_bus.publish("trade_signal", {
            "symbol": "BTCUSDT",
            "action": action,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "score": final
        })

        logger.info(f"TRADE EXECUTED → {action} @ {entry}")

    # -------------------------
    # TICK FLOW — معطّل، الإشارات تجي من SMCEngine فقط
    # -------------------------
    def process_tick(self, data):
        pass  # لا إشارات على التك — SMCEngine يتولى التحليل
