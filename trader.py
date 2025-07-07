# trader.py

import asyncio
import httpx
import hmac
import hashlib
import time
import json
from typing import Optional

class FXOpenTrader:
    def __init__(self, token_id: str, token_key: str, token_secret: str, server_url: str = "https://api.ticktrader.com"):
        self.token_id = token_id
        self.token_key = token_key
        self.token_secret = token_secret.encode('utf-8')
        self.server_url = server_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30)

    def _generate_signature(self, method: str, path: str, nonce: str, body: Optional[str]) -> str:
        msg = self.token_id + method + path + nonce
        if body:
            msg += body
        signature = hmac.new(self.token_secret, msg.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature

    async def _request(self, method: str, path: str, data: Optional[dict] = None):
        url = self.server_url + path
        nonce = str(int(time.time() * 1000))
        body = json.dumps(data) if data else ''
        signature = self._generate_signature(method, path, nonce, body)
        headers = {
            "X-Auth-APIKey": self.token_id,
            "X-Auth-Nonce": nonce,
            "X-Auth-Signature": signature,
            "Content-Type": "application/json",
        }
        try:
            if method == "GET":
                response = await self.client.get(url, headers=headers)
            elif method == "POST":
                response = await self.client.post(url, headers=headers, content=body)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP error during {method} {path}: {e}")

    async def get_account_info(self):
        return await self._request("GET", "/api/v1/account/info")

    async def get_open_positions(self):
        return await self._request("GET", "/api/v1/positions/open")

    async def place_order(self, symbol: str, volume: float, side: str, order_type: str = "market", price: Optional[float] = None, stop_loss: Optional[float] = None, take_profit: Optional[float] = None):
        """
        side: "buy" or "sell"
        order_type: "market" or "limit"
        """
        if side.lower() not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        order = {
            "symbol": symbol,
            "volume": volume,
            "side": side.lower(),
            "type": order_type.lower(),
        }
        if order_type == "limit" and price is None:
            raise ValueError("Limit orders require a price")
        if price is not None:
            order["price"] = price
        if stop_loss is not None:
            order["stop_loss"] = stop_loss
        if take_profit is not None:
            order["take_profit"] = take_profit

        return await self._request("POST", "/api/v1/orders", order)

    async def close_position(self, position_id: str):
        return await self._request("POST", f"/api/v1/positions/{position_id}/close")

    async def close_all_positions(self):
        positions = await self.get_open_positions()
        results = []
        for pos in positions.get("positions", []):
            pos_id = pos.get("id")
            if pos_id:
                result = await self.close_position(pos_id)
                results.append(result)
        return results

    async def shutdown(self):
        await self.client.aclose()

# Example usage (async):
# async def main():
#     trader = FXOpenTrader(token_id="your_token_id", token_key="your_token_key", token_secret="your_token_secret")
#     account_info = await trader.get_account_info()
#     print(account_info)
#     await trader.shutdown()
#
# asyncio.run(main())
