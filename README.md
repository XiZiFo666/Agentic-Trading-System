# Agentic-Trading-System | 多智能体量化交易系统

本项目是一个基于大语言模型（LLM）与 LangGraph 构建的全自动量化交易系统。系统摒弃了单一指标决策，通过构建多角色 AI 智能体（基本面、技术面、情绪面）进行协同研判，引入创新的牛熊逻辑辩论机制过滤模型幻觉，并依托 VaR 风险价值模型实现订单的严格拦截与精准执行。

## 🛠 技术栈重构与升级

为解决传统开源量化项目数据获取不稳定的痛点，本项目在数据链路与执行层进行了深度重构：

- **数据网关**：全面弃用易被封控的 yfinance，接入 **Alpaca API**（毫秒级 K 线/全网新闻）与 **Finnhub**（专业级财务数据）。
- **流程编排**：基于 **LangGraph** 实现 StateGraph 状态机，支持并行的 Fan-out 数据拉取与条件路由（Conditional Edges）。
- **AI 引擎**：支持任意兼容 OpenAI 格式的大模型（GPT-4 / Claude / 深度求索等）作为推理核心。
- **量化指标**：集成 `pandas_ta` 进行 MACD/RSI/布林带等技术计算，结合 `TextBlob` 实时解析新闻情绪。

## 🚀 快速开始
1. 安装依赖
```bash
pip install -r requirements.txt
```
2. 配置环境密钥

在根目录创建 .env 文件，填入你的 API 凭证：
LLM 配置
```bash
OPENAI_API_KEY=你的大模型接口Key
OPENAI_BASE_URL=你的大模型代理地址
```
金融数据与实盘接口
```bash
ALPACA_API_KEY=你的Alpaca_Key
ALPACA_SECRET_KEY=你的Alpaca_Secret
FINNHUB_API_KEY=你的Finnhub_Key
```
3. 运行
```bash
python -m graph.trading_graph
```
