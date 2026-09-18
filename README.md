# Agentic AI Stock Market Prediction System

Goal: Build an agentic AI system to analyse 100 stocks and generate probabilistic buy/sell signals.

## Agents

Technical Agent — analyses price patterns and indicators.

Global News Agent — analyses overall market news and sentiment.

Sector News Agent — analyses sector-specific news and trends.

Stock News Agent — analyses company-specific news.

Social Agent — analyses posts from politicians, policymakers, CEOs and influential investors.

All agents store structured scores and signals in a database.

## Prediction Engine

Combines all signals to estimate:

P(Stock Up)  
P(Stock Down)  
Expected % Move  
Confidence  
Suggested Position Size

## Paper Trading Sandbox

Create a virtual trading environment with fake money, orders, positions, fees and P&L.

Run multiple trading agents with different strategies for 10+ days and compare their performance against the real market and simple benchmarks.

## Future

Use historical backtesting and paper trading to evaluate whether the system produces reliable signals before considering real-money usage.