"""
Aggressive FXOpen Broker Integration for Max Profit
"""

import json
import hmac
import hashlib
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import aiohttp

from config import Config


class FXOpenHandler:
    def __init__(self):
        self.base_url = Config.FXOPEN_BASE_URL.rstrip('/')
        self.api_key = Config.FXOPEN_API_KEY
        self.api_secret = Config.FXOPEN_API_SECRET
        self.login = Config.FXOPEN_LOGIN
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None

        # Aggressive trading control variables
        self.trade_cooldown = timedelta(seconds=10)  # minimum seconds between trades
        self.last_trade_time: Optional[datetime] = None
        self.max_drawdown_pct = 0.15  # 15% max drawdown before emergency close all
        self.recent_wins = 0
        self.recent_losses = 0
        self.performance_window = 20  # last 20 trades for dynamic risk
        self.trade_history: List[Dict[str, Any]] = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    def _generate_signature(self, endpoint: str, payload: str = "") -> Dict[str, str]:
        nonce = str(int(time.time() * 1000))
        message = nonce + endpoint + payload
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return {
            "X-Auth-Apikey": self.api_key,
            "X-Auth-Nonce": nonce,
            "X-Auth-Signature": signature,
            "Content-Type": "application/json"
        }

    async def _make_request(self, method: str, endpoint: str, payload: Any = None) -> Any:
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}{endpoint}"
        payload_str = json.dumps(payload) if payload else ""
        headers = self._generate_signature(endpoint, payload_str)

        try:
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                data=payload_str if payload else None,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:

                response_text = await response.text()

                if response.status == 200:
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        return {"success": True, "data": response_text}
                else:
                    error_msg = f"FXOpen API error: {response.status} - {response_text}"
                    self.logger.error(error_msg)
                    raise Exception(error_msg)

        except asyncio.TimeoutError:
            error_msg = "FXOpen API request timeout"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"FXOpen API request failed: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    # ----- Core Trading API Methods -----

    async def test_connection(self) -> bool:
        try:
            info = await self.get_account_info()
            return info is not None
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    async def get_account_info(self) -> Dict[str, Any]:
        endpoint = f"/accounts/{self.login}"
        return await self._make_request("GET", endpoint)

    async def get_account_balance(self) -> float:
        info = await self.get_account_info()
        try:
            return float(info.get('Balance', 0))
        except Exception:
            return 0.0

    async def get_positions(self) -> List[Dict[str, Any]]:
        endpoint = f"/accounts/{self.login}/positions"
        response = await self._make_request("GET", endpoint)
        if isinstance(response, list):
            return response
        return response.get('positions', [])

    async def close_position(self, position_id: str, volume: Optional[float] = None) -> Dict[str, Any]:
        payload = {'PositionId': position_id}
        if volume:
            payload['Volume'] = float(volume)
        endpoint = f"/accounts/{self.login}/positions/{position_id}/close"
        return await self._make_request("POST", endpoint, payload)

    async def close_all_positions(self) -> List[Dict[str, Any]]:
        positions = await self.get_positions()
        results = []
        for pos in positions:
            pos_id = pos.get('Id') or pos.get('PositionId')
            if pos_id:
                try:
                    res = await self.close_position(pos_id)
                    results.append(res)
                except Exception as e:
                    self.logger.error(f"Failed to close position {pos_id}: {e}")
                    results.append({'error': str(e), 'position_id': pos_id})
        return results

    async def modify_position(self, position_id: str, stop_loss: Optional[float] = None, take_profit: Optional[float] = None) -> Dict[str, Any]:
        payload = {}
        if stop_loss is not None:
            payload['StopLoss'] = float(stop_loss)
        if take_profit is not None:
            payload['TakeProfit'] = float(take_profit)
        if not payload:
            raise ValueError("Must provide stop_loss and/or take_profit")
        endpoint = f"/accounts/{self.login}/positions/{position_id}/modify"
        return await self._make_request("PUT", endpoint, payload)

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        endpoint = f"/symbols/{symbol}/quotes"
        response = await self._make_request("GET", endpoint)
        if response:
            bid = float(response.get('Bid', 0))
            ask = float(response.get('Ask', 0))
            spread = float(response.get('Spread', 0))
            mid_price = (bid + ask) / 2
            return {
                'symbol': symbol,
                'bid': bid,
                'ask': ask,
                'spread': spread,
                'current_price': mid_price,
                'timestamp': datetime.utcnow().isoformat()
            }
        raise Exception(f"No market data for {symbol}")

    async def get_symbols(self) -> List[Dict[str, Any]]:
        endpoint = "/symbols"
        response = await self._make_request("GET", endpoint)
        if isinstance(response, list):
            return response
        return response.get('symbols', [])

    async def place_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        # Enforce cooldown
        if self.last_trade_time and (datetime.utcnow() - self.last_trade_time) < self.trade_cooldown:
            raise Exception("Trade cooldown active - too soon to place another trade")

        # Dynamic risk adjustment based on recent performance
        risk_amount = self.dynamic_risk_amount()

        # Calculate position size with risk adjustment
        position_size = await self.calculate_position_size(
            order_params['symbol'], risk_amount, order_params.get('stop_loss_pips', 20)
        )
        order_params['volume'] = position_size

        # Validate risk/reward before placing
        if not self.validate_risk_reward(
            order_params['entry_price'], order_params.get('stop_loss'), order_params.get('take_profit')
        ):
            raise Exception("Risk:Reward ratio below 1.5 - rejecting trade")

        # Prepare order payload
        payload = {
            'Symbol': order_params['symbol'],
            'Side': order_params['side'].upper(),
            'Volume': position_size,
            'Type': order_params.get('order_type', 'market').upper()
        }
        if 'price' in order_params:
            payload['Price'] = float(order_params['price'])
        if 'stop_loss' in order_params:
            payload['StopLoss'] = float(order_params['stop_loss'])
        if 'take_profit' in order_params:
            payload['TakeProfit'] = float(order_params['take_profit'])
        if 'comment' in order_params:
            payload['Comment'] = order_params['comment']

        response = await self._make_request("POST", f"/accounts/{self.login}/orders", payload)
        self.last_trade_time = datetime.utcnow()
        self.logger.info(f"Placed order: {payload['Symbol']} {payload['Side']} {payload['Volume']} lots")

        # Log trade to history
        self.log_trade(order_params, success=True)
        return response

    async def calculate_position_size(self, symbol: str, risk_amount: float, stop_loss_pips: int) -> float:
        try:
            market_data = await self.get_market_data(symbol)
            symbols = await self.get_symbols()
            symbol_info = next((s for s in symbols if s.get('Symbol') == symbol), None)
            if not symbol_info:
                raise Exception(f"Symbol info not found for {symbol}")

            pip_size = float(symbol_info.get('PipSize', 0.0001))
            lot_size = 100000  # Standard lot

            pip_value = pip_size * lot_size
            risk_per_pip = risk_amount / stop_loss_pips if stop_loss_pips > 0 else risk_amount
            raw_position_size = risk_per_pip / pip_value

            min_lot = float(symbol_info.get('MinLot', 0.01))
            lot_step = float(symbol_info.get('LotStep', 0.01))

            position_size = max(min_lot, (int(raw_position_size / lot_step) * lot_step))
            return round(position_size, 4)

        except Exception as e:
            self.logger.error(f"Position size calculation error: {e}")