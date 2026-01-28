"""Polymarket API client for prediction market data."""

from datetime import datetime, timezone
from typing import Any

import httpx

from polybot.config.settings import get_settings


class PolymarketClient:
    """
    Client for fetching Polymarket prediction market data.

    Note: This client focuses on reading market data. For actual trading,
    additional authentication and Polygon wallet integration would be needed.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        settings = get_settings()
        self.base_url = base_url or settings.polymarket_base_url
        self.api_key = api_key or settings.polymarket_api_key

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self._client = httpx.Client(timeout=30.0, headers=headers)

    def get_markets(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """
        Fetch list of available markets.

        Returns:
            List of market objects with id, question, outcomes, etc.
        """
        response = self._client.get(
            f"{self.base_url}/markets",
            params={"limit": limit, "offset": offset},
        )
        response.raise_for_status()
        return response.json()

    def get_market(self, market_id: str) -> dict[str, Any]:
        """
        Fetch details for a specific market.

        Args:
            market_id: The market's unique identifier

        Returns:
            Market details including current prices
        """
        response = self._client.get(f"{self.base_url}/markets/{market_id}")
        response.raise_for_status()
        return response.json()

    def search_btc_15min_markets(self) -> list[dict[str, Any]]:
        """
        Search for active BTC 15-minute prediction markets.

        Returns:
            List of matching markets
        """
        # Note: The actual Polymarket API search might differ
        # This is a placeholder that would need to be adapted
        # to the actual market naming convention on Polymarket
        markets = self.get_markets(limit=500)

        btc_markets = []
        keywords = ["btc", "bitcoin", "15 min", "15min", "15-min"]

        for market in markets:
            question = market.get("question", "").lower()
            if any(kw in question for kw in keywords):
                btc_markets.append(market)

        return btc_markets

    def get_orderbook(self, token_id: str) -> dict[str, Any]:
        """
        Fetch orderbook for a specific outcome token.

        Args:
            token_id: The outcome token ID

        Returns:
            Orderbook with bids and asks
        """
        response = self._client.get(f"{self.base_url}/book", params={"token_id": token_id})
        response.raise_for_status()
        return response.json()

    def get_midpoint_price(self, token_id: str) -> float | None:
        """
        Get the midpoint price for an outcome token.

        Args:
            token_id: The outcome token ID

        Returns:
            Midpoint price (0-1) or None if no liquidity
        """
        orderbook = self.get_orderbook(token_id)

        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])

        if not bids or not asks:
            return None

        best_bid = float(bids[0]["price"])
        best_ask = float(asks[0]["price"])

        return (best_bid + best_ask) / 2

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Mock client for testing/development when Polymarket is unavailable
class MockPolymarketClient:
    """
    Mock client that simulates Polymarket data for testing.

    Generates realistic-looking 15-min BTC prediction markets.
    """

    def __init__(self):
        self._market_counter = 0

    def generate_mock_market(self, btc_price: float) -> dict[str, Any]:
        """Generate a mock 15-min BTC market based on current price."""
        self._market_counter += 1
        now = datetime.now(timezone.utc)

        # Generate a slightly random price (simulating market inefficiency)
        import random

        # The "fair" probability is around 50%, but markets have noise
        base_prob = 0.50 + random.uniform(-0.15, 0.15)

        return {
            "id": f"mock-btc-15min-{self._market_counter}",
            "question": f"Will BTC be higher than ${btc_price:,.0f} in 15 minutes?",
            "outcomes": ["Yes", "No"],
            "outcomePrices": [str(base_prob), str(1 - base_prob)],
            "volume": random.uniform(1000, 50000),
            "liquidity": random.uniform(5000, 100000),
            "endDate": (now + __import__("datetime").timedelta(minutes=15)).isoformat(),
            "active": True,
            "_mock": True,
        }

    def get_markets(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Return empty list - use generate_mock_market instead."""
        return []

    def search_btc_15min_markets(self) -> list[dict[str, Any]]:
        """Return empty list - use generate_mock_market instead."""
        return []

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
