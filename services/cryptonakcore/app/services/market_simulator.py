import random


class MarketSimulator:
    @staticmethod
    def get_price(sym: str) -> float:
        """
        Simulatore molto semplice:
        - prezzo base 100
        - variazione casuale tra -10 e +10
        Questo rende raggiungibili TP/SL tipo 4.5% / 1.5%
        (tp=104.5, sl=98.5) in pochi tick.
        """
        base = 100.0
        variation = random.uniform(-10.0, 10.0)
        return base + variation
