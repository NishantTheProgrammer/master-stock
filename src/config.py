"""
Central configuration for the Master Stock system.
All settings are loaded from environment variables (.env file).
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Database ---
    database_url: str = "postgresql://postgres:postgres@localhost:5432/master_stock"

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # --- API Keys ---
    finnhub_api_key: str = ""
    alpha_vantage_api_key: str = ""

    # --- Sandbox ---
    sandbox_initial_capital: float = 1_000_000.0  # ₹10 Lakh
    sandbox_transaction_fee_pct: float = 0.001  # 0.1%

    # --- Server ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    dashboard_url: str = "http://localhost:3000"

    # --- Prediction Weights ---
    weight_technical: float = 0.30
    weight_global_news: float = 0.15
    weight_sector_news: float = 0.15
    weight_stock_news: float = 0.25
    weight_social: float = 0.15

    # --- Stock Universe ---
    default_stock_count: int = 20  # Start with 20 stocks for prototyping

    # --- Paths ---
    project_root: Path = Path(__file__).parent.parent

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton settings instance
settings = Settings()

# Stock sectors for Indian market
SECTORS = [
    "IT",
    "Banking",
    "Finance",
    "Pharma",
    "Auto",
    "FMCG",
    "Energy",
    "Metals",
    "Realty",
    "Infrastructure",
    "Telecom",
    "Media",
    "Chemicals",
    "Cement",
    "Consumer Durables",
]

# Default starting stocks (Nifty 20 — top by market cap)
DEFAULT_STOCKS = [
    {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Energy"},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "Banking"},
    {"symbol": "INFY", "name": "Infosys", "sector": "IT"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "Banking"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Telecom"},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking"},
    {"symbol": "ITC", "name": "ITC Limited", "sector": "FMCG"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Banking"},
    {"symbol": "LT", "name": "Larsen & Toubro", "sector": "Infrastructure"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "FMCG"},
    {"symbol": "AXISBANK", "name": "Axis Bank", "sector": "Banking"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "sector": "Finance"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki", "sector": "Auto"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharma"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors", "sector": "Auto"},
    {"symbol": "WIPRO", "name": "Wipro", "sector": "IT"},
    {"symbol": "HCLTECH", "name": "HCL Technologies", "sector": "IT"},
    {"symbol": "TATASTEEL", "name": "Tata Steel", "sector": "Metals"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises", "sector": "Infrastructure"},
]
