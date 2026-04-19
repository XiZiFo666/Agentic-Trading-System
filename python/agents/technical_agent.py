from __future__ import annotations
import json
import datetime
from dataclasses import dataclass
from typing import Any
import pandas as pd
import pandas_ta as ta
import alpaca_trade_api as tradeapi
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from config.settings import CONFIG


@dataclass
class TechnicalAnalysis:
    ticker: str;
    current_price: float;
    macd: float | None;
    macd_signal: float | None;
    macd_histogram: float | None;
    rsi: float | None;
    bb_upper: float | None;
    bb_middle: float | None;
    bb_lower: float | None;
    sma_20: float | None;
    sma_50: float | None;
    volume_trend: str = "NORMAL";
    score: float = 0.0;
    signal: str = "HOLD";
    reasoning: str = ""


class TechnicalAgent:
    SYSTEM_PROMPT = """你是一位技术分析师。输出JSON: {"score": 1-10, "signal": "BUY/SELL/HOLD", "reasoning": "理由"}"""

    def __init__(self):
        self.llm = ChatOpenAI(base_url="https://openrouter.fans/v1", model=CONFIG.llm.model,
                              temperature=CONFIG.llm.temperature, api_key=CONFIG.llm.api_key, max_retries=5)
        self.api = tradeapi.REST(CONFIG.alpaca.api_key, CONFIG.alpaca.secret_key, CONFIG.alpaca.base_url,
                                 api_version='v2')

    def fetch_and_compute(self, ticker: str, period_days: int = 180) -> dict[str, Any]:
        end_dt = datetime.datetime.now()
        start_dt = end_dt - datetime.timedelta(days=period_days)
        try:
            # 优雅地获取半年的无暇 K 线数据
            bars = self.api.get_bars(ticker, tradeapi.TimeFrame.Day, start=start_dt.strftime('%Y-%m-%d'),
                                     end=end_dt.strftime('%Y-%m-%d'), adjustment='all', feed='iex').df
            if bars is None or bars.empty: return {}
            # 将 Alpaca 的小写列名转换为首字母大写，适配 pandas_ta
            df = bars.rename(
                columns={'close': 'Close', 'volume': 'Volume', 'high': 'High', 'low': 'Low', 'open': 'Open'})
        except Exception as e:
            print(f"[Technical] ⚠️ Alpaca获取K线失败: {e}")
            return {}

        try:
            df.ta.macd(append=True);
            df.ta.rsi(append=True);
            df.ta.bbands(append=True);
            df.ta.sma(length=20, append=True);
            df.ta.sma(length=50, append=True)
            latest = df.iloc[-1]
            return {"current_price": latest["Close"], "macd_histogram": latest.get("MACDh_12_26_9"),
                    "rsi": latest.get("RSI_14"), "sma_20": latest.get("SMA_20"), "sma_50": latest.get("SMA_50")}
        except:
            return {}

    def analyze(self, ticker: str) -> TechnicalAnalysis:
        ind = self.fetch_and_compute(ticker)
        if not ind: return TechnicalAnalysis(ticker=ticker, current_price=0, macd=None, macd_signal=None,
                                             macd_histogram=None, rsi=None, bb_upper=None, bb_middle=None,
                                             bb_lower=None, sma_20=None, sma_50=None)

        user_prompt = f"分析技术指标:\n- 价格: ${ind['current_price']:.2f}\n- RSI: {ind.get('rsi')}\n- MACD: {ind.get('macd_histogram')}\n- SMA20: {ind.get('sma_20')}"
        response = self.llm.invoke([SystemMessage(content=self.SYSTEM_PROMPT), HumanMessage(content=user_prompt)])
        try:
            result = json.loads(response.content)
        except:
            result = {"score": 5.0, "signal": "HOLD", "reasoning": "解析失败"}
        return TechnicalAnalysis(ticker=ticker, current_price=ind["current_price"], macd=None, macd_signal=None,
                                 macd_histogram=ind.get("macd_histogram"), rsi=ind.get("rsi"), bb_upper=None,
                                 bb_middle=None, bb_lower=None, sma_20=ind.get("sma_20"), sma_50=ind.get("sma_50"),
                                 score=result.get("score", 5.0), signal=result.get("signal", "HOLD"),
                                 reasoning=result.get("reasoning", ""))

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        a = self.analyze(state["ticker"])
        return {"analyses": [{"agent": "technical", "ticker": state["ticker"], "score": a.score, "signal": a.signal,
                              "reasoning": a.reasoning}]}