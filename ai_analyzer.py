"""
AI Market Analyzer using OpenAI API
Provides market analysis and trading signals
"""

import json
import logging
from typing import Dict, List, Any
from datetime import datetime
import asyncio

from openai import AsyncOpenAI
from config import Config

class AIAnalyzer:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.logger = logging.getLogger(__name__)
        
    async def test_connection(self) -> bool:
        """Test OpenAI API connection"""
        try:
            response = await self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            self.logger.error(f"OpenAI connection test failed: {e}")
            raise
    
    async def analyze_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market data and provide trading recommendations
        
        Args:
            market_data: Dictionary containing price data, indicators, and market info
            
        Returns:
            Dictionary with analysis results and trading signals
        """
        try:
            analysis_prompt = self._prepare_analysis_prompt(market_data)
            
            response = await self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": analysis_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=Config.AI_TEMPERATURE,
                max_tokens=Config.AI_MAX_TOKENS
            )
            
            analysis_result = json.loads(response.choices[0].message.content)
            validated_result = self._validate_analysis_result(analysis_result, market_data)
            self.logger.info(f"AI analysis completed for {market_data.get('symbol', 'unknown')}")
            return validated_result
            
        except Exception as e:
            self.logger.error(f"Error in AI market analysis: {e}")
            return self._get_default_analysis()
    
    def _get_system_prompt(self) -> str:
        return (
            "You are an expert forex trading analyst with deep knowledge of technical analysis, fundamental analysis, and market psychology.\n\n"
            "Your task is to analyze the provided market data and provide a comprehensive trading recommendation.\n\n"
            "You must respond with a JSON object containing:\n"
            "{\n"
            '    "signal": "BUY" | "SELL" | "HOLD",\n'
            '    "confidence": float (0.0 to 1.0),\n'
            '    "entry_price": float,\n'
            '    "stop_loss": float,\n'
            '    "take_profit": float,\n'
            '    "risk_reward_ratio": float,\n'
            '    "analysis": {\n'
            '        "technical": "detailed technical analysis",\n'
            '        "fundamental": "fundamental factors",\n'
            '        "sentiment": "market sentiment analysis",\n'
            '        "risk_factors": ["list of risk factors"]\n'
            '    },\n'
            '    "timeframe": "recommended holding period",\n'
            '    "position_size_percent": float (percentage of account to risk),\n'
            '    "reasons": ["key reasons for the recommendation"]\n'
            "}\n\n"
            "Consider:\n"
            "- Technical indicators and patterns\n"
            "- Support/resistance levels\n"
            "- Market volatility\n"
            "- Economic events and news\n"
            "- Risk management principles\n"
            "- Current market conditions"
        )
    
    def _prepare_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        symbol = market_data.get('symbol', 'Unknown')
        current_price = market_data.get('current_price', 0)
        
        prompt = (
            f"Analyze the following forex market data for {symbol}:\n\n"
            "PRICE DATA:\n"
            f"- Current Price: {current_price}\n"
            f"- Open: {market_data.get('open', 0)}\n"
            f"- High: {market_data.get('high', 0)}\n"
            f"- Low: {market_data.get('low', 0)}\n"
            f"- Previous Close: {market_data.get('prev_close', 0)}\n\n"
            "TECHNICAL INDICATORS:\n"
        )
        
        indicators = market_data.get('indicators', {})
        for indicator, value in indicators.items():
            prompt += f"- {indicator}: {value}\n"
        
        if 'volume' in market_data:
            prompt += f"- Volume: {market_data['volume']}\n"
        if 'spread' in market_data:
            prompt += f"- Spread: {market_data['spread']} pips\n"
        
        if 'timeframe_analysis' in market_data:
            prompt += "\nMULTI-TIMEFRAME ANALYSIS:\n"
            for tf, data in market_data['timeframe_analysis'].items():
                prompt += f"- {tf}: {data}\n"
        
        prompt += (
            f"\nMARKET CONTEXT:\n"
            f"- Trading Session: {market_data.get('session', 'Unknown')}\n"
            f"- Market Volatility: {market_data.get('volatility', 'Normal')}\n"
            f"- Recent News Impact: {market_data.get('news_impact', 'None')}\n\n"
            "Please provide a comprehensive analysis and trading recommendation."
        )
        
        return prompt
    
    def _validate_analysis_result(self, analysis: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            required_fields = ['signal', 'confidence', 'entry_price', 'stop_loss', 'take_profit']
            for field in required_fields:
                if field not in analysis:
                    self.logger.warning(f"Missing required field in AI analysis: {field}")
                    return self._get_default_analysis()
            
            if analysis['signal'] not in ['BUY', 'SELL', 'HOLD']:
                analysis['signal'] = 'HOLD'
            
            confidence = float(analysis.get('confidence', 0.5))
            analysis['confidence'] = max(0.0, min(1.0, confidence))
            
            current_price = market_data.get('current_price', 0)
            if current_price > 0:
                analysis['entry_price'] = float(analysis.get('entry_price', current_price))
                analysis['stop_loss'] = float(analysis.get('stop_loss', current_price))
                analysis['take_profit'] = float(analysis.get('take_profit', current_price))
            
            if 'risk_reward_ratio' not in analysis:
                entry = analysis['entry_price']
                sl = analysis['stop_loss']
                tp = analysis['take_profit']
                
                if analysis['signal'] == 'BUY':
                    risk = abs(entry - sl)
                    reward = abs(tp - entry)
                elif analysis['signal'] == 'SELL':
                    risk = abs(sl - entry)
                    reward = abs(entry - tp)
                else:
                    risk = reward = 1
                
                analysis['risk_reward_ratio'] = reward / risk if risk > 0 else 1.0
            
            analysis['timestamp'] = datetime.utcnow().isoformat()
            analysis['symbol'] = market_data.get('symbol', 'Unknown')
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error validating AI analysis: {e}")
            return self._get_default_analysis()
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        return {
            'signal': 'HOLD',
            'confidence': 0.0,
            'entry_price': 0.0,
            'stop_loss': 0.0,
            'take_profit': 0.0,
            'risk_reward_ratio': 1.0,
            'analysis': {
                'technical': 'Analysis unavailable',
                'fundamental': 'Analysis unavailable',
                'sentiment': 'Neutral',
                'risk_factors': ['AI analysis failed']
            },
            'timeframe': 'Unknown',
            'position_size_percent': 0.0,
            'reasons': ['Default analysis due to AI failure'],
            'timestamp': datetime.utcnow().isoformat(),
            'symbol': 'Unknown'
        }
    
    async def analyze_news_sentiment(self, news_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            if not news_data:
                return {'sentiment': 'neutral', 'impact': 'low', 'confidence': 0.0}
            
            news_text = self._prepare_news_text(news_data)
            
            response = await self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a financial news analyst. Analyze the provided news and assess its potential impact on forex markets.\n\n"
                            "Respond with JSON:\n"
                            "{\n"
                            '    "sentiment": "bullish" | "bearish" | "neutral",\n'
                            '    "impact": "high" | "medium" | "low",\n'
                            '    "confidence": float (0.0 to 1.0),\n'
                            '    "key_factors": ["list of key factors"],\n'
                            '    "affected_currencies": ["list of currency codes"],\n'
                            '    "time_horizon": "immediate" | "short_term" | "medium_term" | "long_term"\n'
                            "}"
                        )
                    },
                    {
                        "role": "user", 
                        "content": f"Analyze this financial news for forex market impact:\n\n{news_text}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            result['timestamp'] = datetime.utcnow().isoformat()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in news