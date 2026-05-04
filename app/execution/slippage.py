import random
import time


def simulate_latency(mean_ms: float = 50.0, std_ms: float = 10.0) -> float:
    """
    Simulates network latency by sleeping for a random delay.
    Returns the actual delay applied (in seconds).
    """
    delay_ms = max(0, random.gauss(mean_ms, std_ms))
    delay_sec = delay_ms / 1000.0
    time.sleep(delay_sec)
    return delay_sec


def compute_slippage(
    order_qty: float,
    avg_depth: float,
    base_slippage: float = 0.0005,
    k: float = 0.1
) -> float:
    """
    Computes slippage percentage based on order size vs market depth.
    - base_slippage: minimum slippage even for small orders
    - k: scaling factor for large orders
    """
    if avg_depth <= 0:
        return base_slippage + k  # fallback worst-case

    ratio = order_qty / avg_depth
    slippage_pct = base_slippage + (k * ratio)
    return slippage_pct


def apply_slippage_to_price(
    mid_price: float,
    slippage_pct: float,
    side: str
) -> float:
    """
    Adjusts the mid price based on slippage and order side.
    BUY  → price increases
    SELL → price decreases
    """
    if side.upper() == "BUY":
        return mid_price * (1 + slippage_pct)
    else:
        return mid_price * (1 - slippage_pct)
