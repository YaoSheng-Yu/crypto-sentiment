# Crypto Sentiment Analysis

Automated crypto news sentiment analysis that runs every 12 hours.

## Features
- Fetches latest crypto news from MediaStack API
- Analyzes sentiment using FinBERT
- Automatically updates every 12 hours
- Stores historical data in monthly JSON files
- Tracks sentiment scores in CSV format

## Setup

1. Fork this repository
2. Add your MediaStack API key:
   - Go to repository Settings > Secrets
   - Add new secret named `MEDIASTACK_API_KEY`
   - Paste your API key as the value

## Data Files
- `data/[YEAR][MONTH].json`: Monthly news articles
- `sentiment_scores.csv`: Historical sentiment scores

## Automatic Updates
The GitHub Action runs every 12 hours to:
1. Fetch new crypto news articles
2. Analyze their sentiment
3. Update the data files
4. Commit changes back to the repository
