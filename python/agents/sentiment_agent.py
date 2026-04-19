from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any
from textblob import TextBlob
import alpaca_trade_api as tradeapi
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from config.settings import CONFIG

@dataclass
class SentimentAnalysis:
    ticker: str; news_sentiment: float; news_count: int; institutional_holders_change: str; analyst_recommendation: str; score: float = 0.0; signal: str = "HOLD"; reasoning: str = ""

class SentimentAgent:
    SYSTEM_PROMPT = """你是一位情绪分析专家。输出JSON: {"score": 1-10, "signal": "BUY/SELL/HOLD", "reasoning": "理由"}"""

    def __init__(self):
        self.llm = ChatOpenAI(base_url="https://openrouter.fans/v1", model=CONFIG.llm.model, temperature=CONFIG.llm.temperature, api_key=CONFIG.llm.api_key, max_retries=5)
        # 初始化正规军 Alpaca 接口
        self.api = tradeapi.REST(CONFIG.alpaca.api_key, CONFIG.alpaca.secret_key, CONFIG.alpaca.base_url, api_version='v2')

    def _analyze_news_sentiment(self, ticker: str) -> tuple[float, int]:
        try:
            # 瞬间获取最新20条官方财经新闻，绝不限流
            news = self.api.get_news(ticker, limit=20)
            sentiments = [TextBlob(n.headline).sentiment.polarity for n in news if hasattr(n, 'headline')]
            return round(sum(sentiments) / len(sentiments), 4) if sentiments else 0.0, len(sentiments)
        except Exception as e:
            print(f"[Sentiment] ⚠️ Alpaca获取新闻失败: {e}")
            return 0.0, 0

    def analyze(self, ticker: str) -> SentimentAnalysis:
        news_sentiment, news_count = self._analyze_news_sentiment(ticker)
        user_prompt = f"分析情绪：\n- 新闻得分: {news_sentiment} (范围-1到+1)\n- 数量: {news_count}\n- 机构: UNKNOWN\n- 评级: HOLD"
        response = self.llm.invoke([SystemMessage(content=self.SYSTEM_PROMPT), HumanMessage(content=user_prompt)])
        try: result = json.loads(response.content)
        except: result = {"score": 5.0, "signal": "HOLD", "reasoning": "解析失败"}
        return SentimentAnalysis(ticker=ticker, news_sentiment=news_sentiment, news_count=news_count, institutional_holders_change="UNKNOWN", analyst_recommendation="HOLD", score=result.get("score", 5.0), signal=result.get("signal", "HOLD"), reasoning=result.get("reasoning", ""))

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        a = self.analyze(state["ticker"])
        return {"analyses": [{"agent": "sentiment", "ticker": state["ticker"], "score": a.score, "signal": a.signal, "reasoning": a.reasoning}]}