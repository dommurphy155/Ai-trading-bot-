# fxopen_api.py

import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode

class FXOpenAPI:
    def __init__(self, token_id, token_key, token_secret, server):
        self.token_id = token_id
        self.token_key = token_key
        self.token_secret = token_secret.encode('utf-8')
        self.server = server.rstrip('/')

    def _generate_signature(self, method, path, nonce, body=''):
        # Construct the message to sign
        message = f'{method}\n{path}\n{nonce}\n{body}'.encode('utf-8')
        signature = hmac.new(self.token_secret, message, hashlib.sha256).hexdigest()
        return signature

    def _headers(self, method, path, body=''):
        nonce = str(int(time.time() * 1000))
        signature = self._generate_signature(method, path, nonce, body)
        return {
            'X-Token-ID': self.token_id,
            'X-Token-Key': self.token_key,
            'X-Nonce': nonce,
            'X-Signature': signature,
            'Content-Type': 'application/json'
        }

    def get_account_info(self):
        path = '/api/v2/account/info'
        url = f'{self.server}{path}'
        headers = self._headers('GET', path)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_open_positions(self):
        path = '/api/v2/positions'
        url = f'{self.server}{path}'
        headers = self._headers('GET', path)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def place_order(self, symbol, volume, order_type, price=None, stop_loss=None, take_profit=None):
        # order_type: 'buy' or 'sell'
        path = '/api/v2/orders'
        url = f'{self.server}{path}'
        order = {
            'symbol': symbol,
            'volume': volume,
            'type': order_type
        }
        if price is not None:
            order['price'] = price
        if stop_loss is not None:
            order['stop_loss'] = stop_loss
        if take_profit is not None:
            order['take_profit'] = take_profit
        import json
        body = json.dumps(order)
        headers = self._headers('POST', path, body)
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status()
        return response.json()

    # Add other API wrapper methods as needed
