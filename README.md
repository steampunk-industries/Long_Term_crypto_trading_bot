# Long\_Term\_crypto\_trading\_bot

**Multi-Currency AI-Augmented Paper & Live Trading Bot**
Supports: KuCoin, Coinbase, Kraken, Gemini, and Steampunk Holdings (API).

---

## 📦 Features

* **Modular Multi-Exchange Support**

  * Plug-and-play integrations for major exchanges
* **Advanced Strategy Layer**

  * RSI-based with market sentiment & symbol ranking
* **Steampunk Holdings Support**

  * Custom API integration with fallback IP
* **Paper + Real Trading Modes**

  * Fully simulated environments with live market data
* **Web Dashboard (Flask + Gunicorn)**

  * Real-time metrics, health checks, visual indicators
* **TensorFlow Ready**

  * Integrated for ML-based forecasting (optional)

---

## 🧱 Project Structure

```
Long_Term_crypto_trading_bot/
├── configs/                    # Static config files (.env, .ini)
├── docker/                     # Dockerfiles and compose YAMLs
├── docs/                       # Markdown documentation
├── scripts/                    # Setup and utility scripts
├── services/                   # .service files for systemd integration
├── src/                        # Core trading bot application
│   ├── exchanges/              # Exchange wrappers (KuCoin, Kraken...)
│   ├── integrations/           # External APIs (Steampunk, Sentiment)
│   ├── strategies/             # Strategy logic
│   ├── utils/                  # Helpers: ranking, data loading, etc
│   ├── database/               # SQLAlchemy models, sessions
├── tests/                      # Test scripts and coverage
├── requirements.txt            # Pinned runtime dependencies
└── README.md                   # You are here
```

---

## 🚀 Quickstart

### 1. 🧪 Set up environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 🔐 Configure API Keys

Copy `.env.example` to `.env` and fill in exchange keys.

### 3. 🛠️ Run in paper trading mode

```bash
./run_multi_currency_bot.py --exchange kucoin --paper --dry-run --once --max-positions 3
```

### 4. 🌐 Start the dashboard

```bash
./scripts/run_dashboard.sh
```

Then visit: [http://localhost:8000](http://localhost:8000)

---

## 🧠 Strategy Overview

* **RSI Signal Generation**
* **Symbol Ranking**: weighted by volatility, volume, and sentiment
* **Position Sizing**: capital-preserving max allocation
* **Steampunk Holdings Override**: API pricing fallback or strategy influence

---

## 🐳 Docker Support

Build the full app + dashboard via Compose:

```bash
docker-compose -f docker/docker-compose.cpu.yml up --build
```

---

## 🧼 Maintenance

To audit for dead code or unused scripts:

```bash
./scripts/audit_repo_usage.sh   # Prints audit report
./scripts/final_cleanup.sh      # Auto-deletes flagged files
```

---

## 📜 License

MIT. Steampunk Holdings modules may be subject to private licensing.

---

## 🧭 Roadmap

* [ ] Deploy AWS Lambda price fetcher
* [ ] Add Discord webhook alerts
* [ ] Integrate TensorFlow forecasting pipeline
* [ ] Auto-detect high volatility symbols

---

## 🤝 Contributions

PRs welcome. See `docs/CONTRIBUTING.md` (coming soon).

---

> Project initiated by Steampunk Industries. Designed for scalable, modular long-term automated crypto trading.
