from __future__ import annotations
import json
import requests
from dataclasses import dataclass
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from config.settings import CONFIG

# >>> 填入你刚才在 Finnhub 申请的免费 API Key <<<
FINNHUB_API_KEY = "d7ic6ohr01qu8vfo3pb0d7ic6ohr01qu8vfo3pbg"

@dataclass
class FundamentalAnalysis:
    ticker: str; pe_ratio: float | None; pb_ratio: float | None; roe: float | None; revenue_growth: float | None; profit_margin: float | None; debt_to_equity: float | None; free_cash_flow: float | None; score: float = 0.0; signal: str = "HOLD"; reasoning: str = ""

class FundamentalAgent:
    SYSTEM_PROMPT = """你是一位基本面分析师。基于指标评分(1-10)。输出JSON: {"score": 1-10, "signal": "BUY/SELL/HOLD", "reasoning": "理由"}"""

    def __init__(self):
        self.llm = ChatOpenAI(base_url="https://openrouter.fans/v1", model=CONFIG.llm.model, temperature=CONFIG.llm.temperature, api_key=CONFIG.llm.api_key, max_retries=5)

    def fetch_fundamentals(self, ticker: str) -> dict[str, Any]:
        # 彻底抛弃雅虎，使用 Finnhub 毫秒级极速接口获取专业财报
        url = f"https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={FINNHUB_API_KEY}"
        try:
            res = requests.get(url, timeout=15).json()
            metrics = res.get('metric', {})
            return {
                "pe_ratio": metrics.get("peExclExtraTTM"), "pb_ratio": metrics.get("pbAnnual"),
                "roe": metrics.get("roeTTM"), "revenue_growth": metrics.get("revenueGrowthTTMYoy"),
                "profit_margin": metrics.get("netMarginTTM"), "debt_to_equity": metrics.get("totalDebt/totalEquityAnnual"),
                "free_cash_flow": None,
            }
        except Exception as e:
            print(f"[Fundamental] ⚠️ 获取基本面失败: {e}")
            return {}

    def analyze(self, ticker: str) -> FundamentalAnalysis:
        f = self.fetch_fundamentals(ticker)
        user_prompt = f"分析基本面:\nPE: {f.get('pe_ratio')}\nPB: {f.get('pb_ratio')}\nROE: {f.get('roe')}\n营收增长: {f.get('revenue_growth')}\n利润率: {f.get('profit_margin')}\n负债率: {f.get('debt_to_equity')}"
        response = self.llm.invoke([SystemMessage(content=self.SYSTEM_PROMPT), HumanMessage(content=user_prompt)])
        try: result = json.loads(response.content)
        except: result = {"score": 5.0, "signal": "HOLD", "reasoning": "解析失败"}
        return FundamentalAnalysis(ticker=ticker, pe_ratio=f.get("pe_ratio"), pb_ratio=f.get("pb_ratio"), roe=f.get("roe"), revenue_growth=f.get("revenue_growth"), profit_margin=f.get("profit_margin"), debt_to_equity=f.get("debt_to_equity"), free_cash_flow=None, score=result.get("score", 5.0), signal=result.get("signal", "HOLD"), reasoning=result.get("reasoning", ""))

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        a = self.analyze(state["ticker"])
        return {"analyses": [{"agent": "fundamental", "ticker": state["ticker"], "score": a.score, "signal": a.signal, "reasoning": a.reasoning}]}