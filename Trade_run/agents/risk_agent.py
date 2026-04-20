from __future__ import annotations
import json
import datetime
from dataclasses import dataclass
from typing import Any
import numpy as np
import alpaca_trade_api as tradeapi
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from config.settings import CONFIG


@dataclass
class RiskAssessment:
    approved: bool;
    risk_score: float;
    var_95: float;
    max_position_allowed: float;
    hard_rule_violations: list[str];
    soft_warnings: list[str];
    adjusted_position_pct: float;
    stop_loss: float;
    take_profit: float;
    reasoning: str


class RiskAgent:
    SYSTEM_PROMPT = """你是一位风控官。输出JSON: {"approved": true/false, "adjusted_position_pct": 0-1, "soft_warnings": [], "reasoning": "理由"}"""

    def __init__(self):
        self.llm = ChatOpenAI(base_url="https://openrouter.fans/v1", model=CONFIG.llm.model, temperature=0.1,
                              api_key=CONFIG.llm.api_key, max_retries=5)
        self.risk_config = CONFIG.risk
        self.api = tradeapi.REST(CONFIG.alpaca.api_key, CONFIG.alpaca.secret_key, CONFIG.alpaca.base_url,
                                 api_version='v2')

    def _calculate_var(self, ticker: str) -> float:
        end_dt = datetime.datetime.now()
        start_dt = end_dt - datetime.timedelta(days=365)
        try:
            bars = self.api.get_bars(ticker, tradeapi.TimeFrame.Day, start=start_dt.strftime('%Y-%m-%d'),
                                     end=end_dt.strftime('%Y-%m-%d'), adjustment='all', feed='iex').df
            if bars is None or bars.empty: return 0.05
            returns = bars['close'].pct_change().dropna()
            return abs(float(np.percentile(returns, 5)))
        except:
            return 0.05

    def assess(self, ticker: str, debate_result: dict, portfolio_state: dict | None = None) -> RiskAssessment:
        var_95 = self._calculate_var(ticker)
        user_prompt = f"风控评估：\n标的: {ticker}\n建议仓位: {debate_result.get('target_position_pct', 0.0)}\nVaR: {var_95}"
        response = self.llm.invoke([SystemMessage(content=self.SYSTEM_PROMPT), HumanMessage(content=user_prompt)])
        try:
            result = json.loads(response.content)
        except:
            result = {"approved": False, "adjusted_position_pct": 0.0, "reasoning": "解析失败"}

        current_price = 0
        try:
            current_price = self.api.get_latest_trade(ticker, feed='iex').price
        except:
            pass

        return RiskAssessment(approved=result.get("approved", False), risk_score=var_95 * 100, var_95=var_95,
                              max_position_allowed=0.1, hard_rule_violations=[], soft_warnings=[],
                              adjusted_position_pct=result.get("adjusted_position_pct", 0),
                              stop_loss=current_price * 0.95, take_profit=current_price * 1.1,
                              reasoning=result.get("reasoning", ""))

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        a = self.assess(state["ticker"], state.get("debate_result", {}), state.get("portfolio_state"))
        return {"risk_assessment": {"approved": a.approved, "risk_score": a.risk_score, "var_95": a.var_95,
                                    "adjusted_position_pct": a.adjusted_position_pct, "reasoning": a.reasoning}}