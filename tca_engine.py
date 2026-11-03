"""Small auditable TCA calculation engine; price units are per share.

All sign conventions are positive = worse for the investor.
No assumption that a market trade is a client fill.
"""
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ParentOrder:
    order_id: str
    side: str
    quantity: int
    arrival_price: float
    end_price: float

    def __post_init__(self):
        if self.side not in ("BUY", "SELL") or self.quantity <= 0:
            raise ValueError("Invalid side or quantity")
        if self.arrival_price <= 0 or self.end_price <= 0:
            raise ValueError("Prices must be positive")


@dataclass(frozen=True)
class Fill:
    parent_id: str
    child_id: str
    minute: int
    quantity: int
    price: float
    fee: float = 0.0

    def __post_init__(self):
        if self.minute < 0 or self.quantity <= 0 or self.price <= 0 or self.fee < 0:
            raise ValueError("Invalid fill")


def analyse(parent: ParentOrder, fills: Sequence[Fill], market_vwap: float):
    if market_vwap <= 0:
        raise ValueError("Invalid VWAP")
    if any(f.parent_id != parent.order_id for f in fills):
        raise ValueError("Parent mismatch")
    executed = sum(f.quantity for f in fills)
    if executed > parent.quantity:
        raise ValueError("Overfilled parent")
    sign = 1 if parent.side == "BUY" else -1
    gross = sum(sign * f.quantity * (f.price - parent.arrival_price) for f in fills)
    opportunity = sign * (parent.quantity - executed) * (parent.end_price - parent.arrival_price)
    fees = sum(f.fee for f in fills)
    notional = parent.quantity * parent.arrival_price
    avg_price = sum(f.price*f.quantity for f in fills)/executed if executed else None
    vwap_slippage = sign*(avg_price-market_vwap)/market_vwap*10000 if avg_price else None
    return {
        "fill_rate": executed/parent.quantity,
        "executed_quantity": executed,
        "average_fill_price": avg_price,
        "executed_arrival_cost": gross,
        "opportunity_cost": opportunity,
        "fees": fees,
        "implementation_shortfall": gross+opportunity+fees,
        "implementation_shortfall_bps": (gross+opportunity+fees)/notional*10000,
        "vwap_slippage_bps": vwap_slippage,
    }


def effective_spread_bps(side: str, execution_price: float, midpoint: float):
    if side not in ("BUY", "SELL") or midpoint <= 0 or execution_price <= 0:
        raise ValueError("Invalid input")
    sign = 1 if side == "BUY" else -1
    return 2*sign*(execution_price-midpoint)/midpoint*10000


def realised_spread_bps(side: str, execution_price: float, future_midpoint: float):
    if side not in ("BUY", "SELL") or future_midpoint <= 0 or execution_price <= 0:
        raise ValueError("Invalid input")
    sign = 1 if side == "BUY" else -1
    return 2*sign*(execution_price-future_midpoint)/future_midpoint*10000
