import json
import logging
from typing import Dict, Any
from datetime import datetime
import httpx
import asyncio

from config import Config

class AIAnalyzer:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.hf_token = Config.HF_API_TOKEN  # Set this in your config
        self.hf_model = Config.HF_MODEL_NAME  # e.g. "gpt2" or your preferred HF model
        self.api_url = f"https://api-inference.huggingface.co/models/{self.hf_model}"
        self.headers = {"Authorization": f"Bearer {self.hf_token}"}
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_connection(self) -> bool:
        """Test HF API connection by sending a simple prompt"""
        try:
            payload = {"inputs": "Test connection"}
            response = await self.client.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            self.logger.error(f"Hugging Face connection test failed: {e}")
            raise

    async def analyze_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = self._prepare_analysis_prompt(market_data)
            response_text = await self._call_hf_api(prompt)
            analysis_result = self._parse_response(response_text)
            validated_result = self._validate_analysis_result(analysis_result, market_data)
            self.logger.info(f"HF AI analysis completed for {market_data.get('symbol', 'unknown')}")
            return validated_result
        except Exception as e:
            self.logger.error(f"Error in AI market analysis: {e}")
            return self._get_default_analysis()

    async def _call_hf_api(self, prompt: str) -> str:
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": Config.AI_MAX_TOKENS,
                "temperature": Config.AI_TEMPERATURE,
                "return_full_text": False,
            }
        }
        try:
            response = await self.client.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # HF generative models return list of dicts with 'generated_text' key
            if isinstance(data, list) and len(data) > 0 and 'generated_text' in data[0]:
                return data[0]['generated_text']
            elif isinstance(data, dict) and 'error' in data:
                raise RuntimeError(f"Hugging Face API error: {data['error']}")
            else:
                return str(data)
        except Exception as e:
            self.logger.error(f"HF API call failed: {e}")
            raise

    def _prepare_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        symbol = market_data.get("symbol", "Unknown")
        current_price = market_data.get("current_price", 0)
        prompt = (
            f"Analyze the following forex market data for {symbol}:\n\n"
            f"PRICE DATA:\n"
            f"- Current Price: {current_price}\n"
            f"- Open: {market_data.get('open', 0)}\n"
            f"- High: {market_data.get('high', 0)}\n"
            f"- Low: {market_data.get('low', 0)}\n"
            f"- Previous Close: {market_data.get('prev_close', 0)}\n\n"
            "TECHNICAL INDICATORS:\n"
        )
        indicators = market_data.get("indicators", {})
        for indicator, value in indicators.items():
            prompt += f"- {indicator}: {value}\n"
        if "volume" in market_data:
            prompt += f"- Volume: {market_data['volume']}\n"
        if "spread" in market_data:
            prompt += f"- Spread: {market_data['spread']} pips\n"
        if "timeframe_analysis" in market_data:
            prompt += "\nMULTI-TIMEFRAME ANALYSIS:\n"
            for tf, data in market_data["timeframe_analysis"].items():
                prompt += f"- {tf}: {data}\n"
        prompt += (
            f"\nMARKET CONTEXT:\n"
            f"- Trading Session: {market_data.get('session', 'Unknown')}\n"
            f"- Market Volatility: {market_data.get('volatility', 'Normal')}\n"
            f"- Recent News Impact: {market_data.get('news_impact', 'None')}\n\n"
            "Please provide a trading recommendation in JSON format with fields:\n"
            "signal (BUY, SELL, HOLD), confidence (0.0 to 1.0), entry_price, stop_loss, take_profit,\n"
            "risk_reward_ratio, analysis details, timeframe, position_size_percent, reasons."
        )
        return prompt

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Attempt to parse AI response as JSON, fallback to empty analysis"""
        try:
            # Some HF models output text directly without JSON structure
            # Try extracting JSON from text if present
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                json_text = text[start:end]
                return json.loads(json_text)
            else:
                self.logger.warning("No JSON object found in HF response, returning default analysis")
                return self._get_default_analysis()
        except Exception as e:
            self.logger.error(f"Error parsing HF response JSON: {e}")
            return self._get_default_analysis()

    def _validate_analysis_result(self, analysis: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            required_fields = ["signal", "confidence", "entry_price", "stop_loss", "take_profit"]
            for field in required_fields:
                if field not in analysis:
                    self.logger.warning(f"Missing required field in AI analysis: {field}")
                    return self._get_default_analysis()

            if analysis["signal"] not in ["BUY", "SELL", "HOLD"]:
                analysis["signal"] = "HOLD"

            confidence = float(analysis.get("confidence", 0.5))
            analysis["confidence"] = max(0.0, min(1.0, confidence))

            current_price = market_data.get("current_price", 0)
            if current_price > 0:
                analysis["entry_price"] = float(analysis.get("entry_price", current_price))
                analysis["stop_loss"] = float(analysis.get("stop_loss", current_price))
                analysis["take_profit"] = float(analysis.get("take_profit", current_price))

            if "risk_reward_ratio" not in analysis:
                entry = analysis["entry_price"]
                sl = analysis["stop_loss"]
                tp = analysis["take_profit"]

                if analysis["signal"] == "BUY":
                    risk = abs(entry - sl)
                    reward = abs(tp - entry)
                elif analysis["signal"] == "SELL":
                    risk = abs(sl - entry)
                    reward = abs(entry - tp)
                else:
                    risk = reward = 1.0

                analysis["risk_reward_ratio"] = reward / risk if risk > 0 else 1.0

            analysis["timestamp"] = datetime.utcnow().isoformat()
            analysis["symbol"] = market_data.get("symbol", "Unknown")

            return analysis

        except Exception as e:
            self.logger.error(f"Error validating AI analysis: {e}")
            return self._get_default_analysis()

    def _get_default_analysis(self) -> Dict[str, Any]:
        return {
            "signal": "HOLD",
            "confidence": 0.0,
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "risk_reward_ratio": 1.0,
            "analysis": {
                "technical": "Analysis unavailable",
                "fundamental": "Analysis unavailable",
                "sentiment": "Neutral",
                "risk_factors": ["AI analysis failed"],
            },
            "timeframe": "Unknown",
            "position_size_percent": 0.0,
            "reasons": ["Default analysis due to AI failure"],
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": "Unknown",
        }

    async def close(self):
        await self.client.aclose()