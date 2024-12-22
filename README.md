# Crypto Sentiment Analysis Dashboard

A real-time cryptocurrency sentiment analysis dashboard that tracks market sentiment through news articles.

## Features

- Automated news fetching from MediaStack API
- Sentiment analysis using FinBERT and RoBERTa models
- Interactive dashboard for sentiment visualization
- Daily updates of crypto-related news
- Historical sentiment tracking

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your MediaStack API key in `config.py`

3. Initialize the data directory:
```bash
python scripts/setup_directories.py
```

4. Run the dashboard:
```bash
python app.py
```

## Project Structure

- `app.py`: Main dashboard application
- `scripts/`
  - `fetch_news.py`: News fetching script
  - `analyze_sentiment.py`: Sentiment analysis script
  - `update_data.py`: Data update automation
- `data/`: JSON files containing news articles and sentiment scores
- `models/`: Sentiment analysis models and utilities
- `static/`: Dashboard static files
- `templates/`: Dashboard HTML templates

## Automated Updates

The project includes automated scripts for:
- Daily news fetching
- Sentiment analysis
- Data updates
- GitHub synchronization

## License

MIT License
