"""
AI Market Analyzer using OpenAI API
Provides market analysis and trading signals
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import aiohttp

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
            # Prepare market data for AI analysis
            analysis_prompt = self._prepare_analysis_prompt(market_data)
            
            # Get AI analysis
            response = await self.client.chat.completions.create(
                model=Config.AI_MODEL,  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=Config.AI_TEMPERATURE,
                max_tokens=Config.AI_MAX_TOKENS
            )
            
            # Parse AI response
            analysis_result = json.loads(response.choices[0].message.content)
            
            # Validate and enhance the analysis
            validated_result = self._validate_analysis_result(analysis_result, market_data)
            
            self.logger.info(f"AI analysis completed for {market_data.get('symbol', 'unknown')}")
            return validated_result
            
        except Exception as e:
            self.logger.error(f"Error in AI market analysis: {e}")
            return self._get_default_analysis()
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for AI analysis"""
        return """You are an expert forex trading analyst with deep knowledge of technical analysis, fundamental analysis, and market psychology. 

Your task is to analyze the provided market data and provide a comprehensive trading recommendation.

You must respond with a JSON object containing:
{
    "signal": "BUY" | "SELL" | "HOLD",
    "confidence": float (0.0 to 1.0),
    "entry_price": float,
    "stop_loss": float,
    "take_profit": float,
    "risk_reward_ratio": float,
    "analysis": {
        "technical": "detailed technical analysis",
        "fundamental": "fundamental factors",
        "sentiment": "market sentiment analysis",
        "risk_factors": ["list of risk factors"]
    },
    "timeframe": "recommended holding period",
    "position_size_percent": float (percentage of account to risk),
    "reasons": ["key reasons for the recommendation"]
}

Consider:
- Technical indicators and patterns
- Support/resistance levels
- Market volatility
- Economic events and news
- Risk management principles
- Current market conditions
"""
    
    def _prepare_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """Prepare the analysis prompt with market data"""
        symbol = market_data.get('symbol', 'Unknown')
        current_price = market_data.get('current_price', 0)
        
        prompt = f"""
Analyze the following forex market data for {symbol}:

PRICE DATA:
- Current Price: {current_price}
- Open: {market_data.get('open', 0)}
- High: {market_data.get('high', 0)}
- Low: {market_data.get('low', 0)}
- Previous Close: {market_data.get('prev_close', 0)}

TECHNICAL INDICATORS:
"""
        
        # Add technical indicators if available
        indicators = market_data.get('indicators', {})
        for indicator, value in indicators.items():
            prompt += f"- {indicator}: {value}\n"
        
        # Add volume and spread data
        if 'volume' in market_data:
            prompt += f"- Volume: {market_data['volume']}\n"
        if 'spread' in market_data:
            prompt += f"- Spread: {market_data['spread']} pips\n"
        
        # Add timeframe analysis
        if 'timeframe_analysis' in market_data:
            prompt += "\nMULTI-TIMEFRAME ANALYSIS:\n"
            for tf, data in market_data['timeframe_analysis'].items():
                prompt += f"- {tf}: {data}\n"
        
        # Add market context
        prompt += f"""
MARKET CONTEXT:
- Trading Session: {market_data.get('session', 'Unknown')}
- Market Volatility: {market_data.get('volatility', 'Normal')}
- Recent News Impact: {market_data.get('news_impact', 'None')}

Please provide a comprehensive analysis and trading recommendation.
"""
        
        return prompt
    
    def _validate_analysis_result(self, analysis: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enhance AI analysis result"""
        try:
            # Ensure required fields exist
            required_fields = ['signal', 'confidence', 'entry_price', 'stop_loss', 'take_profit']
            for field in required_fields:
                if field not in analysis:
                    self.logger.warning(f"Missing required field in AI analysis: {field}")
                    return self._get_default_analysis()
            
            # Validate signal
            if analysis['signal'] not in ['BUY', 'SELL', 'HOLD']:
                analysis['signal'] = 'HOLD'
            
            # Validate confidence (0.0 to 1.0)
            confidence = float(analysis.get('confidence', 0.5))
            analysis['confidence'] = max(0.0, min(1.0, confidence))
            
            # Validate prices
            current_price = market_data.get('current_price', 0)
            if current_price > 0:
                analysis['entry_price'] = float(analysis.get('entry_price', current_price))
                analysis['stop_loss'] = float(analysis.get('stop_loss', current_price))
                analysis['take_profit'] = float(analysis.get('take_profit', current_price))
            
            # Calculate risk-reward ratio if not provided
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
            
            # Add timestamp
            analysis['timestamp'] = datetime.utcnow().isoformat()
            analysis['symbol'] = market_data.get('symbol', 'Unknown')
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error validating AI analysis: {e}")
            return self._get_default_analysis()
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Get default analysis when AI analysis fails"""
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
        """
        Analyze news sentiment and its potential market impact
        
        Args:
            news_data: List of news articles with title, content, and metadata
            
        Returns:
            Dictionary with sentiment analysis and market impact assessment
        """
        try:
            if not news_data:
                return {'sentiment': 'neutral', 'impact': 'low', 'confidence': 0.0}
            
            # Prepare news for analysis
            news_text = self._prepare_news_text(news_data)
            
            response = await self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a financial news analyst. Analyze the provided news and assess its potential impact on forex markets.

Respond with JSON:
{
    "sentiment": "bullish" | "bearish" | "neutral",
    "impact": "high" | "medium" | "low",
    "confidence": float (0.0 to 1.0),
    "key_factors": ["list of key factors"],
    "affected_currencies": ["list of currency codes"],
    "time_horizon": "immediate" | "short_term" | "medium_term" | "long_term"
}"""
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
            self.logger.error(f"Error in news sentiment analysis: {e}")
            return {'sentiment': 'neutral', 'impact': 'low', 'confidence': 0.0, 'error': str(e)}
    
    def _prepare_news_text(self, news_data: List[Dict[str, Any]]) -> str:
        """Prepare news text for sentiment analysis"""
        news_text = ""
        for article in news_data[:5]:  # Limit to 5 most recent articles
            title = article.get('title', '')
            content = article.get('content', '')[:200]  # Limit content length
            timestamp = article.get('timestamp', '')
            
            news_text += f"Title: {title}\nContent: {content}\nTime: {timestamp}\n\n"
        
        return news_text
    
    async def get_market_outlook(self, timeframe: str = "daily") -> Dict[str, Any]:
        """
        Get general market outlook and trading recommendations
        
        Args:
            timeframe: Analysis timeframe (daily, weekly, monthly)
            
        Returns:
            Dictionary with market outlook and recommendations
        """
        try:
            current_date = datetime.utcnow().strftime("%Y-%m-%d")
            
            response = await self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a senior forex market analyst. Provide a {timeframe} market outlook for major currency pairs.

Respond with JSON:
{{
    "outlook": "bullish" | "bearish" | "neutral",
    "confidence": float (0.0 to 1.0),
    "key_themes": ["list of key market themes"],
    "currency_rankings": {{
        "strongest": ["currency codes"],
        "weakest": ["currency codes"]
    }},
    "major_levels": {{
        "EURUSD": {{"support": float, "resistance": float}},
        "GBPUSD": {{"support": float, "resistance": float}},
        "USDJPY": {{"support": float, "resistance": float}}
    }},
    "risk_factors": ["list of risk factors"],
    "recommendations": ["trading recommendations"]
}}"""
                    },
                    {
                        "role": "user",
                        "content": f"Provide a {timeframe} forex market outlook for {current_date}. Consider current economic conditions, central bank policies, geopolitical factors, and technical analysis."
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
                max_tokens=800
            )
            
            outlook = json.loads(response.choices[0].message.content)
            outlook['timestamp'] = datetime.utcnow().isoformat()
            outlook['timeframe'] = timeframe
            
            return outlook
            
        except Exception as e:
            self.logger.error(f"Error getting market outlook: {e}")
            return {
                'outlook': 'neutral',
                'confidence': 0.0,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
