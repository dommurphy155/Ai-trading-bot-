# fxopen_handler.py
import time
import hmac
import hashlib
import requests
import json

class FXOpenAPIError(Exception):
    pass

class FXOpenHandler:
    """
    FXOpen TickTrader Web API Client for trading automation.
    Authenticated requests using HMAC.
    """

    def __init__(self, token_id: str, token_key: str, token_secret: str, base_url: str = 'https://api.fxopen.com'):
        self.token_id = token_id
        self.token_key = token_key
        self.token_secret = token_secret.encode()
        self.base_url = base_url.rstrip('/')

    def _get_headers(self, method: str, path: str, body: str = '') -> dict:
        """
        Generate auth headers with HMAC signature required by FXOpen API.
        """
        timestamp = str(int(time.time() * 1000))
        message = (self.token_key + method.upper() + path + body + timestamp).encode()
        signature = hmac.new(self.token_secret, message, hashlib.sha256).hexdigest()
        return {
            'X-Auth-Timestamp': timestamp,
            'X-Auth-Key': self.token_key,
            'X-Auth-Signature': signature,
            'Content-Type': 'application/json',
        }

    def _request(self, method: str, path: str, data: dict = None) -> dict:
        """
        Perform HTTP request with auth headers and error handling.
        """
        url = self.base_url + path
        body = json.dumps(data) if data else ''
        headers = self._get_headers(method, path, body)

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, data=body)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, data=body)
            else:
                raise FXOpenAPIError(f'Unsupported HTTP method: {method}')
        except requests.RequestException as e:
            raise FXOpenAPIError(f'HTTP request failed: {e}')

        if not response.ok:
            raise FXOpenAPIError(f'API error {response.status_code}: {response.text}')

        try:
            return response.json()
        except json.JSONDecodeError:
            raise FXOpenAPIError('Failed to decode JSON response')

    def get_account_info(self) -> dict:
        """Get account information."""
        return self._request('GET', '/api/v1/account-info')

    def get_open_positions(self) -> dict:
        """Get all open positions."""
        return self._request('GET', '/api/v1/open-positions')

    def get_orders(self) -> dict:
        """Get current orders."""
        return self._request('GET', '/api/v1/orders')

    def place_order(self, symbol: str, volume: float, order_type: str = 'BUY', price: float = None,
                    stop_loss: float = None, take_profit: float = None, client_order_id: str = None) -> dict:
        """
        Place a new order.
        order_type: 'BUY' or 'SELL'
        volume: lots
        price: optional limit price for limit orders
        stop_loss, take_profit: optional prices
        client_order_id: optional unique client ID
        """
        data = {
            "symbol": symbol,
            "volume": volume,
            "orderType": order_type.upper()
        }
        if price is not None:
            data["price"] = price
        if stop_loss is not None:
            data["stopLoss"] = stop_loss
        if take_profit is not None:
            data["takeProfit"] = take_profit
        if client_order_id is not None:
            data["clientOrderId"] = client_order_id

        return self._request('POST', '/api/v1/place-order', data)

    def close_position(self, position_id: str) -> dict:
        """Close an open position by its ID."""
        data = {"positionId": position_id}
        return self._request('POST', '/api/v1/close-position', data)

    def cancel_order(self, order_id: str) -> dict:
        """Cancel an existing order by order ID."""
        path = f'/api/v1/cancel-order/{order_id}'
        return self._request('POST', path)

    def get_order_status(self, order_id: str) -> dict:
        """Get status of a specific order."""
        path = f'/api/v1/order-status/{order_id}'
        return self._request('GET', path)
