"""Polymarket API client for prediction market data."""

from datetime import datetime, timezone
from typing import Any

import httpx

from polybot.config.settings import get_settings


# BTC 15-minute Up/Down series ID on Polymarket
BTC_15MIN_SERIES_ID = 10192

# Gamma API for event/series data
GAMMA_API_URL = "https://gamma-api.polymarket.com"

# CLOB API for orderbook data
CLOB_API_URL = "https://clob.polymarket.com"


class PolymarketClient:
    """
    Client for fetching Polymarket prediction market data.

    Uses Gamma API for BTC 15-minute markets (series-based)
    and CLOB API for orderbook data.
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
        Fetch list of available markets from CLOB API.

        Returns:
            List of market objects with id, question, outcomes, etc.
        """
        response = self._client.get(
            f"{self.base_url}/markets",
            params={"limit": limit, "offset": offset},
        )
        response.raise_for_status()
        data = response.json()
        # API returns {'data': [...]} or just [...]
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data if isinstance(data, list) else []

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

    def get_btc_15min_markets(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Fetch active BTC 15-minute Up/Down markets from Gamma API.

        Uses the series_id=10192 which contains all BTC 15-min markets.

        Returns:
            List of active markets with prices, token IDs, etc.
        """
        response = self._client.get(
            f"{GAMMA_API_URL}/events",
            params={
                "series_id": BTC_15MIN_SERIES_ID,
                "closed": "false",
                "limit": limit,
            },
        )
        response.raise_for_status()
        data = response.json()

        # Parse the events into a standard format
        markets = []
        for event in data:
            # Each event has markets array with the Up/Down outcomes
            event_markets = event.get("markets", [])
            if not event_markets:
                continue

            market = event_markets[0]  # There's usually one market per event
            tokens = market.get("clobTokenIds", [])
            prices = market.get("outcomePrices", "[]")

            # Parse prices (comes as JSON string)
            if isinstance(prices, str):
                try:
                    import json
                    prices = json.loads(prices)
                except:
                    prices = ["0.50", "0.50"]

            # Extract outcome prices
            up_price = float(prices[0]) if len(prices) > 0 else 0.50
            down_price = float(prices[1]) if len(prices) > 1 else 0.50

            markets.append({
                "id": event.get("id", ""),
                "slug": event.get("slug", ""),
                "title": event.get("title", ""),
                "question": market.get("question", event.get("title", "")),
                "description": event.get("description", ""),
                "outcomes": market.get("outcomes", "[]"),
                "outcomePrices": [str(up_price), str(down_price)],
                "up_price": up_price,
                "down_price": down_price,
                "up_token_id": tokens[0] if len(tokens) > 0 else None,
                "down_token_id": tokens[1] if len(tokens) > 1 else None,
                "condition_id": market.get("conditionId", ""),
                "end_date": event.get("endDate", ""),
                "volume": float(event.get("volume", 0) or 0),
                "liquidity": float(event.get("liquidity", 0) or 0),
                "active": not event.get("closed", True),
                "_source": "gamma_api",
            })

        return markets

    def search_btc_15min_markets(self) -> list[dict[str, Any]]:
        """
        Search for active BTC 15-minute prediction markets.

        Returns:
            List of matching markets with real Polymarket odds.
        """
        try:
            markets = self.get_btc_15min_markets(limit=5)
            # Filter only active markets
            return [m for m in markets if m.get("active", False)]
        except Exception as e:
            # Fallback to old method if Gamma API fails
            print(f"Gamma API failed: {e}, falling back to CLOB search")
            return self._search_btc_markets_fallback()

    def _search_btc_markets_fallback(self) -> list[dict[str, Any]]:
        """Fallback search using CLOB API keywords."""
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
        response = self._client.get(
            f"{CLOB_API_URL}/book",
            params={"token_id": token_id}
        )
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
        try:
            orderbook = self.get_orderbook(token_id)

            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            if not bids or not asks:
                return None

            best_bid = float(bids[0]["price"])
            best_ask = float(asks[0]["price"])

            return (best_bid + best_ask) / 2
        except Exception:
            return None

    def get_current_btc_market(self) -> dict[str, Any] | None:
        """
        Get the currently active BTC 15-minute market.

        Returns the market that is currently open for trading
        (not yet resolved).

        Returns:
            Market dict or None if no active market found.
        """
        markets = self.search_btc_15min_markets()
        if not markets:
            return None

        # Return the first active market (closest to resolution)
        return markets[0]

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
            "outcomes": ["Up", "Down"],
            "outcomePrices": [str(base_prob), str(1 - base_prob)],
            "up_price": base_prob,
            "down_price": 1 - base_prob,
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

    def get_current_btc_market(self) -> dict[str, Any] | None:
        """Return None - use generate_mock_market instead."""
        return None

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
