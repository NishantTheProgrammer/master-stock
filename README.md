# Master Stock — Agentic AI Stock Market Prediction System

A full-stack, AI-powered system designed to analyze the Indian stock market (NSE/BSE), generate probabilistic buy/sell signals, and test strategies in a paper trading sandbox. 

## Features

### 🤖 5 Specialized AI Agents
*   **Technical Agent:** Computes pure mathematical indicators (RSI, MACD, Bollinger Bands, Crossovers).
*   **Global News Agent:** Uses **FinBERT** and **Ollama (Llama 3.1)** to assess overall market sentiment.
*   **Sector News Agent:** Analyzes industry trends and caches scores for sector-wide efficiency.
*   **Stock News Agent:** Scores company-specific catalysts, earnings, and events.
*   **Social Agent:** Tracks retail sentiment via Stocktwits, weighting posts by author influence.

### 🎯 Prediction Engine
Aggregates all 5 agent signals using weighted sigmoid functions to estimate:
*   P(Stock Up) & P(Stock Down)
*   Expected % Move
*   Confidence & Suggested Position Size

### 🏦 Paper Trading Sandbox
A virtual trading environment containing multiple independent strategy agents:
*   **Momentum Strategy** (Aggressive trend rider)
*   **Contrarian Strategy** (Mean reversion, buys fear)
*   **Balanced Strategy** (Moderate conviction, 20% cash reserve)
*   **Conservative Strategy** (High conviction only, tight stop-losses)

### 📊 Next.js Dashboard
A premium, dark-mode web UI with dynamic gauges, performance leaderboards, and real-time prediction tracking.

---

## Getting Started (Docker Installation)

The entire project is Dockerized for easy setup.

### Prerequisites
*   [Docker](https://docs.docker.com/get-docker/) & Docker Compose
*   [Ollama](https://ollama.com/) (Running on your local host machine)
*   [Finnhub API Key](https://finnhub.io/register) (Free tier)

### 1. Setup Environment Variables
Copy the template and add your API keys:
```bash
cp .env.example .env
# Edit .env and add FINNHUB_API_KEY and ALPHA_VANTAGE_API_KEY
```

*Note: The Docker containers are configured to automatically connect to Ollama running natively on your machine via `host.docker.internal`.*

### 2. Start the Stack
Spin up the Database, FastAPI Backend, and Next.js Frontend:
```bash
docker compose up -d --build
```
*(PostgreSQL data is automatically persisted to `./postgres_data/` in your project folder).*

### 3. Initialize & Run from the Dashboard
Open your browser and navigate to:
**[http://localhost:3000](http://localhost:3000)**

At the top of the dashboard, you will find the **System Controls** panel. Click the buttons in this order:
1. **Initialize DB**: Seeds the database with the Nifty Top 20 stocks.
2. **Fetch Data**: Downloads historical price data (default 365 days) for the stocks.
3. **Run Predictions**: Executes the AI Agents to generate market predictions.
4. **Simulate**: Runs the Sandbox paper trading simulation to see how strategies perform.

---

## Future Roadmap
- Use historical backtesting and paper trading to evaluate whether the system produces reliable signals before considering real-money usage.
- Expand stock universe from Nifty Top 20 to 100+ stocks.
- Support pluggable cloud LLMs (OpenAI/Anthropic).