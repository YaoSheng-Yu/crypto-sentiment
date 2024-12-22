import os
from pathlib import Path
import requests
import json
from datetime import datetime, timezone, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NewsManager:
    def __init__(self):
        self.api_key = os.getenv('MEDIASTACK_API_KEY')
        if not self.api_key:
            raise ValueError("MEDIASTACK_API_KEY environment variable is not set")
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)
        self.base_url = "http://api.mediastack.com/v1/news"

    def fetch_news(self, from_date, to_date, limit=10):
        params = {
            'access_key': self.api_key,
            'keywords': 'crypto, bitcoin',
            'languages': 'en',
            'sort': 'popularity',
            'limit': limit,
            'date': f"{from_date},{to_date}",
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                logging.error(f"API Error: {data['error']}")
                return None
                
            articles = data.get('data', [])
            logging.info(f"API returned {len(articles)} articles")
            
            if articles:
                # Get existing articles
                monthly_file = self.data_dir / f"{datetime.now(timezone.utc).year}{datetime.now(timezone.utc).strftime('%b')}.json"
                existing_articles = self.get_existing_articles(monthly_file)
                existing_content = {(article['title'].strip().lower(), article['url'].strip().lower()) 
                                 for article in existing_articles}
                
                # Process new articles
                processed_articles = []
                seen_content = set()
                
                for article in articles:
                    if len(processed_articles) >= 5:
                        break
                        
                    if article.get('url') and article.get('title'):
                        title = article.get('title', '').strip().lower()
                        url = article.get('url', '').strip().lower()
                        content_key = (title, url)
                        
                        if content_key not in existing_content and content_key not in seen_content:
                            seen_content.add(content_key)
                            processed_articles.append({
                                'title': article.get('title', '').strip(),
                                'description': article.get('description', '').strip(),
                                'url': article.get('url', '').strip(),
                                'source': {'name': article.get('source', '')},
                                'published_at': article.get('published_at', '')
                            })
                
                if processed_articles:
                    # Save to temp file for analysis
                    temp_filename = self.data_dir / 'temp.json'
                    with open(temp_filename, 'w', encoding='utf-8') as f:
                        json.dump(processed_articles, f, indent=4, ensure_ascii=False)
                    logging.info(f"Saved {len(processed_articles)} new articles")
                    
                    # Update monthly file
                    self.update_monthly_file(monthly_file)
                    
                    # Run sentiment analysis
                    from analyze_sentiment import analyze_new_articles
                    analyze_new_articles()
                    
                    return True
                    
            return False
                
        except Exception as e:
            logging.error(f"Error fetching news: {e}")
            return False

    def get_existing_articles(self, file_path):
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error reading existing articles: {e}")
        return []

    def update_monthly_file(self, file_path):
        temp_file = self.data_dir / 'temp.json'
        if not temp_file.exists():
            return
        
        try:
            # Read new articles
            with open(temp_file, 'r', encoding='utf-8') as f:
                new_articles = json.load(f)
            
            # Read existing articles
            existing_articles = self.get_existing_articles(file_path)
            
            # Add new articles at the beginning
            updated_articles = new_articles + existing_articles
            
            # Save updated file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(updated_articles, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Updated {file_path.name} with {len(new_articles)} articles")
            
        except Exception as e:
            logging.error(f"Error updating monthly file: {e}")

def main():
    news_manager = NewsManager()
    
    # Get dates for API
    current_date = datetime.now(timezone.utc)
    latest_date = current_date - timedelta(days=1)
    
    from_date = latest_date.strftime('%Y-%m-%d')
    to_date = current_date.strftime('%Y-%m-%d')
    
    logging.info(f"Fetching news from {from_date} to {to_date}")
    
    if news_manager.fetch_news(from_date, to_date, limit=10):
        logging.info("Successfully updated news and sentiment")
    else:
        logging.error("Failed to update news")

if __name__ == "__main__":
    main()
