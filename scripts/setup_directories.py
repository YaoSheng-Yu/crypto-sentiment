import os
import shutil
import json
import requests
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class MediaStackCollector:
    def __init__(self):
        self.api_key = '7eb65cde9504f2206c3ead3c589ef541'
        self.base_url = "http://api.mediastack.com/v1/news"
        self.articles = []

    def fetch_articles(self, date_range, limit=30):

        params = {
            'access_key': self.api_key,
            'keywords': 'crypto, bitcoin',
            'languages': 'en',
            'sort': 'popularity',
            'limit': limit,
            'date': date_range
        }

        try:
            logging.info(f"Sending request with params: {params}")
            response = requests.get(self.base_url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    logging.info(f"Found {len(data['data'])} articles")
                    for article in data['data']:
                        if article.get('url') and article.get('title'):  # Ensure URL and title exist
                            self.articles.append({
                                'title': article.get('title', '').strip(),
                                'description': article.get('description', '').strip(),
                                'url': article.get('url', '').strip(),
                                'source': {'name': article.get('source', '')},
                                'published_at': article.get('published_at', '')
                            })
                return True
            else:
                logging.error(f"Error {response.status_code}: {response.text}")
                return False
        except Exception as e:
            logging.error(f"Exception during API request: {str(e)}")
            return False

    def save_to_json(self, filename):
        """Save collected articles to JSON file, sorted by published_at date"""
        if self.articles:
            # Sort articles by published_at date, newest first
            sorted_articles = sorted(
                self.articles,
                key=lambda x: x['published_at'] if x['published_at'] else '',
                reverse=True  # newest first
            )
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(sorted_articles, f, indent=2, ensure_ascii=False)
            logging.info(f"Saved {len(sorted_articles)} articles to {filename}")
        else:
            logging.warning("No articles to save")

def main():
    collector = MediaStackCollector()
    
    date_range = "2024-12-18,2024-12-21"
    logging.info(f"Fetching news for date range: {date_range}")
    
    if collector.fetch_articles(date_range, limit=30):
        collector.save_to_json('data/2024Dec.json')
    else:
        logging.error("Failed to fetch articles")

if __name__ == "__main__":
    main()
