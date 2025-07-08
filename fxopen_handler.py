"""
FXOpen Broker Integration
Handles trading operations and account management
"""

import json
import hmac
import hashlib
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiohttp

from config import Config

class FXOpenHandler:
    def __init__(self):
        self.base_url = Config.FXOPEN_BASE_URL
        self.api_key = Config.FXOPEN_API_KEY
        self.api_secret = Config.FXOPEN_API_SECRET
        self.login = Config.FXOPEN_LOGIN
        self.logger = logging.getLogger(__name__)
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _generate_signature(self, endpoint: str, payload: str = "") -> Dict[str, str]:
        """Generate HMAC signature for FXOpen API authentication"""
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
    
    async def _make_request(self, method: str, endpoint: str, payload: Dict = None) -> Dict[str, Any]:
        """Make authenticated request to FXOpen API"""
        if not self.session:
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
    
    async def test_connection(self) -> bool:
        """Test FXOpen API connection"""
        try:
            account_info = await self.get_account_info()
            return account_info is not None
        except Exception as e:
            self.logger.error(f"FXOpen connection test failed: {e}")
            raise
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            endpoint = f"/accounts/{self.login}"
            response = await self._make_request("GET", endpoint)
            
            self.logger.debug("Account info retrieved successfully")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            raise
    
    async def get_account_balance(self) -> float:
        """Get current account balance"""
        try:
            account_info = await self.get_account_info()
            return float(account_info.get('Balance', 0))
        except Exception as e:
            self.logger.error(f"Failed to get account balance: {e}")
            return 0.0
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        try:
            endpoint = f"/accounts/{self.login}/positions"
            response = await self._make_request("GET", endpoint)
            
            positions = response if isinstance(response, list) else response.get('positions', [])
            self.logger.debug(f"Retrieved {len(positions)} open positions")
            return positions
            
        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            return []
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get current market data for a symbol"""
        try:
            endpoint = f"/symbols/{symbol}/quotes"
            response = await self._make_request("GET", endpoint)
            
            if response:
                market_data = {
                    'symbol': symbol,
                    'bid': float(response.get('Bid', 0)),
                    'ask': float(response.get('Ask', 0)),
                    'spread': float(response.get('Spread', 0)),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Calculate current price as mid-price
                market_data['current_price'] = (market_data['bid'] + market_data['ask']) / 2
                
                return market_data
            else:
                raise Exception(f"No market data received for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Failed to get market data for {symbol}: {e}")
            raise
    
    async def get_historical_data(self, symbol: str, timeframe: str, count: int = 100) -> List[Dict[str, Any]]:
        """Get historical price data"""
        try:
            endpoint = f"/symbols/{symbol}/history"
            params = {
                'timeframe': timeframe,
                'count': count
            }
            
            response = await self._make_request("GET", endpoint, params)
            
            if isinstance(response, list):
                return response
            else:
                return response.get('data', [])
                
        except Exception as e:
            self.logger.error(f"Failed to get historical data for {symbol}: {e}")
            return []
    
    async def place_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place a trading order
        
        Args:
            order_params: Dictionary containing order parameters
                - symbol: Trading symbol
                - side: 'buy' or 'sell'
                - volume: Order volume
                - order_type: 'market' or 'limit'
                - price: Order price (for limit orders)
                - stop_loss: Stop loss price
                - take_profit: Take profit price
        """
        try:
            # Validate order parameters
            required_params = ['symbol', 'side', 'volume']
            for param in required_params:
                if param not in order_params:
                    raise ValueError(f"Missing required parameter: {param}")
            
            # Prepare order payload
            payload = {
                'Symbol': order_params['symbol'],
                'Side': order_params['side'].upper(),
                'Volume': float(order_params['volume']),
                'Type': order_params.get('order_type', 'market').upper()
            }
            
            # Add optional parameters
            if 'price' in order_params:
                payload['Price'] = float(order_params['price'])
            
            if 'stop_loss' in order_params:
                payload['StopLoss'] = float(order_params['stop_loss'])
            
            if 'take_profit' in order_params:
                payload['TakeProfit'] = float(order_params['take_profit'])
            
            if 'comment' in order_params:
                payload['Comment'] = order_params['comment']
            
            endpoint = f"/accounts/{self.login}/orders"
            response = await self._make_request("POST", endpoint, payload)
            
            self.logger.info(f"Order placed successfully: {order_params['symbol']} {order_params['side']} {order_params['volume']}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")
            raise
    
    async def close_position(self, position_id: str, volume: float = None) -> Dict[str, Any]:
        """Close a position (partially or fully)"""
        try:
            payload = {
                'PositionId': position_id
            }
            
            if volume:
                payload['Volume'] = float(volume)
            
            endpoint = f"/accounts/{self.login}/positions/{position_id}/close"
            response = await self._make_request("POST", endpoint, payload)
            
            self.logger.info(f"Position closed: {position_id}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to close position {position_id}: {e}")
            raise
    
    async def close_all_positions(self) -> List[Dict[str, Any]]:
        """Close all open positions"""
        results = []
        try:
            positions = await self.get_positions()
            
            for position in positions:
                try:
                    position_id = position.get('Id') or position.get('PositionId')
                    if position_id:
                        result = await self.close_position(position_id)
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Failed to close position {position_id}: {e}")
                    results.append({'error': str(e), 'position_id': position_id})
            
            self.logger.info(f"Closed {len(results)} positions")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to close all positions: {e}")
            raise
    
    async def modify_position(self, position_id: str, stop_loss: float = None, take_profit: float = None) -> Dict[str, Any]:
        """Modify position stop loss and/or take profit"""
        try:
            payload = {}
            
            if stop_loss is not None:
                payload['StopLoss'] = float(stop_loss)
            
            if take_profit is not None:
                payload['TakeProfit'] = float(take_profit)
            
            if not payload:
                raise ValueError("At least one parameter (stop_loss or take_profit) must be provided")
            
            endpoint = f"/accounts/{self.login}/positions/{position_id}/modify"
            response = await self._make_request("PUT", endpoint, payload)
            
            self.logger.info(f"Position modified: {position_id}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to modify position {position_id}: {e}")
            raise
    
    async def get_order_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get order history"""
        try:
            endpoint = f"/accounts/{self.login}/orders/history"
            params = {'limit': limit}
            
            response = await self._make_request("GET", endpoint, params)
            
            if isinstance(response, list):
                return response
            else:
                return response.get('orders', [])
                
        except Exception as e:
            self.logger.error(f"Failed to get order history: {e}")
            return []
    
    async def get_symbols(self) -> List[Dict[str, Any]]:
        """Get available trading symbols"""
        try:
            endpoint = "/symbols"
            response = await self._make_request("GET", endpoint)
            
            if isinstance(response, list):
                return response
            else:
                return response.get('symbols', [])
                
        except Exception as e:
            self.logger.error(f"Failed to get symbols: {e}")
            return []
    
    async def calculate_position_size(self, symbol: str, risk_amount: float, stop_loss_pips: int) -> float:
        """Calculate position size based on risk amount and stop loss"""
        try:
            market_data = await self.get_market_data(symbol)
            
            # Get symbol information for pip value calculation
            symbols = await self.get_symbols()
            symbol_info = next((s for s in symbols if s.get('Symbol') == symbol), None)
            
            if not symbol_info:
                raise Exception(f"Symbol information not found for {symbol}")
            
            # Calculate pip value (simplified - may need adjustment based on symbol)
            pip_size = float(symbol_info.get('PipSize', 0.0001))
            
            # Calculate position size
            # Risk per pip = risk_amount / stop_loss_pips
            # Position size = risk_per_pip / pip_value
            
            # For most forex pairs, pip value = pip_size * lot_size
            # Simplified calculation - in real implementation, consider account currency
            pip_value = pip_size * 100000  # Standard lot
            risk_per_pip = risk_amount / stop_loss_pips
            position_size = risk_per_pip / pip_value
            
            # Round to appropriate lot size
            min_lot = float(symbol_info.get('MinLot', 0.01))
            lot_step = float(symbol_info.get('LotStep', 0.01))
            
            position_size = round(position_size / lot_step) * lot_step
            position_size = max(position_size, min_lot)
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Failed to calculate position size: {e}")
            return 0.01  # Default minimum lot size
