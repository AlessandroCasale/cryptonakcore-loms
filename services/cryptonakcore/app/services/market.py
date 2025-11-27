
# app/services/market.py
from typing import Optional

# Prezzo di mercato simulato (parte da 60000)
market_price: float = 60000.0

def get_market_price() -> float:
    """Ritorna il prezzo di mercato simulato."""
    return market_price

def set_market_price(price: float):
    """Setta manualmente il prezzo simulato (per test)."""
    global market_price
    market_price = price
