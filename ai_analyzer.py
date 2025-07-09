"""
AI Market Analyzer using Hugging Face Inference API
Provides market analysis and trading signals
"""

import json
import logging
from typing import Dict, List, Any
from datetime import datetime
import httpx
from config import Config

class AIAnalyzer:
    def __init__(self) -> None:
        self.token = Config.HF_TOKEN
        self.model = Config.HF_MODEL
        self.logger = logging.getLogger(__name__)
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model}"

    async def test_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(self.api_url, headers=self.headers, json={"inputs": "Hello"})
                return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Hugging Face connection test failed: {e}")
            raise

    async def analyze_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = self._prepare_analysis_prompt(market_data)
            payload = {"inputs": prompt}

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(self.api_url, headers=self.headers, json=payload)

            content = response.json()
            if isinstance(content, dict) and "error" in content:
                raise Exception(content["error"])

            if isinstance(content, list) and isinstance(content[0], dict) and "generated_text" in content[0]:
                text = content[0]["generated_text"]
                analysis_result = json.loads(text)
            else:
                raise Exception("Unexpected Hugging Face response")

            validated = self._validate_analysis_result(analysis_result, market_data)
            self.logger.info(f"AI analysis completed for {market_data.get('symbol', 'unknown')}")
            return validated

        except Exception as e:
            self.logger.error(f"Error in Hugging Face AI analysis: {e}")
            return self._get_default_analysis()

    def _prepare_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        return (
            "You are a professional forex analyst. Based on the following data, respond ONLY with a JSON object "
            "containing: signal (BUY/SELL/HOLD), confidence (0.0–1.0), entry_price, stop_loss, take_profit, "
            "risk_reward_ratio, and analysis breakdown.\n\n"
            f"Symbol: {market_data.get('symbol')}\n"
            f"Current Price: {market_data.get('current_price')}\n"
            f"Indicators: {market_data.get('indicators')}\n"
            f"Volume: {market_data.get('volume')}\n"
            f"Session: {market_data.get('session')}\n"
            f"News Impact: {market_data.get('news_impact')}\n\n"
            "JSON:"
        )

    def _validate_analysis_result(self, analysis: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            required_fields = ["signal", "confidence", "entry_price", "stop_loss", "take_profit"]
            for field in required_fields:
                if field not in analysis:
                    self.logger.warning(f"Missing field in AI analysis: {field}")
                    return self._get_default_analysis()

            if analysis["signal"] not in ["BUY", "SELL", "HOLD"]:
                analysis["signal"] = "HOLD"

            analysis["confidence"] = max(0.0, min(1.0, float(analysis.get("confidence", 0.5))))
            current_price = market_data.get("current_price", 0)
            analysis["entry_price"] = float(analysis.get("entry_price", current_price))
            analysis["stop_loss"] = float(analysis.get("stop_loss", current_price))
            analysis["take_profit"] = float(analysis.get("take_profit", current_price))

            if "risk_reward_ratio" not in analysis:
                entry = analysis["entry_price"]
                sl = analysis["stop_loss"]
                tp = analysis["take_profit"]
                risk = abs(entry - sl)
                reward = abs(tp - entry)
                analysis["risk_reward_ratio"] = reward / risk if risk > 0 else 1.0

            analysis["timestamp"] = datetime.utcnow().isoformat()
            analysis["symbol"] = market_data.get("symbol", "Unknown")

            return analysis

        except Exception as e:
            self.logger.error(f"Error validating analysis: {e}")
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
                "technical": "Unavailable",
                "fundamental": "Unavailable",
                "sentiment": "Neutral",
                "risk_factors": ["Default fallback"]
            },
            "timeframe": "N/A",
            "position_size_percent": 0.0,
            "reasons": ["Hugging Face fallback used"],
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": "Unknown"
        }