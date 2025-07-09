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

        # Aggressive trading controls
        self.trade_cooldown = timedelta(seconds=10)  # Min seconds between trades
        self.last_trade_time: Optional[datetime] = None
        self.max_drawdown_pct = 0.15  # 15% max drawdown threshold
        self.recent_wins = 0
        self.recent_losses = 0
        self.performance_window = 20  # Last 20 trades for dynamic risk
        self.trade_history: List[Dict[str, Any]] = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session and not self.session.closed:
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
                text = await response.text()
                if response.status == 200:
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return {"success": True, "data": text}
                else:
                    err = f"FXOpen API error: {response.status} - {text}"
                    self.logger.error(err)
                    raise Exception(err)
        except asyncio.TimeoutError:
            err = "FXOpen API request timeout"
            self.logger.error(err)
            raise Exception(err)
        except Exception as e:
            err = f"FXOpen API request failed: {str(e)}"
            self.logger.error(err)
            raise Exception(err)

    # Core API Methods

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
        resp = await self._make_request("GET", endpoint)
        if isinstance(resp, list):
            return resp
        return resp.get('positions', [])

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
        if stop_loss is None and take_profit is None:
            raise ValueError("Must provide stop_loss and/or take_profit")
        payload = {}
        if stop_loss is not None:
            payload['StopLoss'] = float(stop_loss)
        if take_profit is not None:
            payload['TakeProfit'] = float(take_profit)
        endpoint = f"/accounts/{self.login}/positions/{position_id}/modify"
        return await self._make_request("PUT", endpoint, payload)

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        endpoint = f"/symbols/{symbol}/quotes"
        resp = await self._make_request("GET", endpoint)
        if resp:
            bid = float(resp.get('Bid', 0))
            ask = float(resp.get('Ask', 0))
            spread = float(resp.get('Spread', 0))
            mid = (bid + ask) / 2
            return {
                'symbol': symbol,
                'bid': bid,
                'ask': ask,
                'spread': spread,
                'current_price': mid,
                'timestamp': datetime.utcnow().isoformat()
            }
        raise Exception(f"No market data for {symbol}")

    async def get_symbols(self) -> List[Dict[str, Any]]:
        endpoint = "/symbols"
        resp = await self._make_request("GET", endpoint)
        if isinstance(resp, list):
            return resp
        return resp.get('symbols', [])

    async def place_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        # Enforce trade cooldown
        if self.last_trade_time and (datetime.utcnow() - self.last_trade_time) < self.trade_cooldown:
            raise Exception("Trade cooldown active - too soon to place another trade")

        risk_amount = self.dynamic_risk_amount()

        position_size = await self.calculate_position_size(
            order_params['symbol'], risk_amount, order_params.get('stop_loss_pips', 20)
        )
        order_params['volume'] = position_size

        if not self.validate_risk_reward(
            order_params['entry_price'], order_params.get('stop_loss'), order_params.get('take_profit')
        ):
            raise Exception("Risk:Reward ratio below 1.5 - rejecting trade")

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

        resp = await self._make_request("POST", f"/accounts/{self.login}/orders", payload)
        self.last_trade_time = datetime.utcnow()
        self.logger.info(f"Placed order: {payload['Symbol']} {payload['Side']} {payload['Volume']} lots")
        self.log_trade(order_params, success=True)
        return resp

    async def calculate_position_size(self, symbol: str, risk_amount: float, stop_loss_pips: int) -> float:
        try:
            market_data = await self.get_market_data(symbol)
            symbols = await self.get_symbols()
            symbol_info = next((s for s in symbols if s.get('Symbol') == symbol), None)
            if not symbol_info:
                raise Exception(f"Symbol info not found for {symbol}")

            pip_size = float(symbol_info.get('PipSize', 0.0001))
            lot_size = 100000  # Standard lot size

            pip_value = pip_size * lot_size
            risk_per_pip = risk_amount / stop_loss_pips if stop_loss_pips > 0 else risk_amount
            raw_position_size = risk_per_pip / pip_value

            min_lot = float(symbol_info.get('MinLot', 0.01))
            lot_step = float(symbol_info.get('LotStep', 0.01))

            position_size = max(min_lot, (int(raw_position_size / lot_step) * lot_step))
            return round(position_size, 4)

        except Exception as e:
            self.logger.error(f"Position size calculation error: {e}")
            raise

    def dynamic_risk_amount(self) -> float:
        """Calculate risk amount based on recent performance"""
        # Basic placeholder: risk more after wins, less after losses
        base_risk = 100  # $100 base risk per trade
        performance_factor = (self.recent_wins - self.recent_losses) / max(self.performance_window, 1)
        adjusted_risk = base_risk * (1 + performance_factor)
        adjusted_risk = max(20, min(adjusted_risk, 500))  # Clamp risk between $20 and $500
        return adjusted_risk

    def validate_risk_reward(self, entry_price: float, stop_loss: Optional[float], take_profit: Optional[float]) -> bool:
        """Check if risk:reward >= 1.5"""
        if stop_loss is None or take_profit is None:
            return False
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        if risk == 0:
            return False
        ratio = reward / risk
        return ratio >= 1.5

    def log_trade(self, order_params: Dict[str, Any], success: bool) -> None:
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": order_params.get("symbol"),
            "side": order_params.get("side"),
            "volume": order_params.get("volume"),
            "entry_price": order_params.get("entry_price"),
            "stop_loss": order_params.get("stop_loss"),
            "take_profit": order_params.get("take_profit"),
            "success": success,
        }
        self.trade_history.append(record)
        # Maintain only recent trades
        if len(self.trade_history) > self.performance_window:
            self.trade_history.pop(0)
        if success:
            self.recent_wins += 1
        else:
            self.recent_losses += 1