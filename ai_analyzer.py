import os
import openai

class AIAnalyzer:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")

    async def analyze(self, symbol, price):
        prompt = (
            f"Given current price {price:.5f} for {symbol}, "
            "should we BUY, SELL, or HOLD? "
            "Return JSON: {\"signal\":\"BUY/SELL/HOLD\",\"confidence\":float}."
        )
        resp = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        data = eval(resp.choices[0].message.content)
        return data["signal"], data["confidence"]
